#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import * as ccc from "@ckb-ccc/core";
import { HDKey } from "@scure/bip32";
import { mnemonicToSeedSync } from "@scure/bip39";

import { buildOnchainFixtureRecipePayload } from "./fixture_recipes.ts";

export const DEFAULT_PATH = "m/44'/309'/0'/0/0";
export const DEFAULT_EXTERNAL_PATH = "m/44'/309'/0'/0/1";
const DEFAULT_FEE_RATE = 1000;
const DEFAULT_SELF_TRANSFER_CKB = "62";
const DEFAULT_OUT_DIR = "generated";
const DEFAULT_CASE_FILE = "generated.cases.json";
const DEFAULT_FIXTURE_RECIPE_FILE = "recipes.onchain-fixtures.generated.json";
const WAIT_TRANSACTION_TIMEOUT_MS = 180_000;

export type Network = "Mainnet" | "Testnet";
export type RecipeKind =
  | "self_transfer"
  | "transfer"
  | "multi_output"
  | "mixed_lock_groups"
  | "custom_lock_output"
  | "custom_type_outputs"
  | "xudt_mint"
  | "xudt_transfer"
  | "dao_deposit"
  | "dao_withdraw1"
  | "two_stage_same_lock"
  | "two_stage_witness_payload"
  | "many_inputs_one_output"
  | "two_stage_many_inputs_one_output";
export type SignaturePolicy = "ignore" | "compare" | "require";

export type RawOutput = {
  to_address?: string;
  amount_ckb?: string;
  data?: string;
};

export type RawRecipe = {
  name?: string;
  kind?: RecipeKind | string;
  network?: Network | string;
  from_address?: string;
  path?: string;
  transport?: string;
  signature_policy?: SignaturePolicy | string;
  fee_rate?: number;
  rpc_url?: string;
  wait_committed?: boolean;
  to_address?: string;
  amount_ckb?: string;
  secondary_amount_ckb?: string;
  funding_amount_ckb?: string;
  funding_output_count?: number;
  output_data?: string;
  witness_input_type?: string;
  witness_output_type?: string;
  primary_witness_input_type?: string;
  primary_witness_output_type?: string;
  secondary_witness_input_type?: string;
  secondary_witness_output_type?: string;
  trailing_witness?: string;
  same_group_second_witness?: string;
  extra_known_cell_deps?: string[];
  custom_lock_hash_type?: string;
  custom_lock_args?: string;
  custom_type_hash_types?: string[];
  custom_type_args?: string;
  xudt_amount?: string;
  xudt_change_amount?: string;
  xudt_cell_capacity_ckb?: string;
  target_input_count?: number;
  outputs?: RawOutput[];
  min_input_count?: number;
  secondary_address?: string;
  secondary_path?: string;
  primary_input_count?: number;
  secondary_input_count?: number;
};

export type RecipePayload = {
  defaults?: RawRecipe;
  recipes?: RawRecipe[];
};

export type NormalizedOutput = {
  toAddress: string;
  amountShannons: bigint;
  data: `0x${string}`;
};

export type NormalizedRecipe = {
  name: string;
  kind: RecipeKind;
  network: Network;
  fromAddress: string;
  path: string;
  transport: string;
  signaturePolicy: SignaturePolicy;
  feeRate: number;
  rpcUrl?: string;
  waitCommitted: boolean;
  toAddress?: string;
  amountShannons?: bigint;
  secondaryAmountShannons?: bigint;
  fundingAmountShannons?: bigint;
  fundingOutputCount?: number;
  outputData?: `0x${string}`;
  witnessInputType?: `0x${string}`;
  witnessOutputType?: `0x${string}`;
  primaryWitnessInputType?: `0x${string}`;
  primaryWitnessOutputType?: `0x${string}`;
  secondaryWitnessInputType?: `0x${string}`;
  secondaryWitnessOutputType?: `0x${string}`;
  trailingWitness?: `0x${string}`;
  sameGroupSecondWitness?: `0x${string}`;
  extraKnownCellDeps?: string[];
  customLockHashType?: ccc.HashType;
  customLockArgs?: `0x${string}`;
  customTypeHashTypes?: ccc.HashType[];
  customTypeArgs?: `0x${string}`;
  xudtAmount?: bigint;
  xudtChangeAmount?: bigint;
  xudtCellCapacityShannons?: bigint;
  targetInputCount?: number;
  outputs?: NormalizedOutput[];
  minInputCount?: number;
  secondaryAddress?: string;
  secondaryPath?: string;
  primaryInputCount?: number;
  secondaryInputCount?: number;
};

type SubmittedTx = {
  name: string;
  txHash: string;
};

type PrepareResult = {
  name: string;
  txHash: string | null;
  status: "not_sent" | "sent";
};

export type TrezorSignTxJson = {
  inputs: {
    tx_hash: string;
    index: number;
    since: number;
  }[];
  outputs: {
    capacity: number;
    lock_code_hash: string;
    lock_hash_type: number;
    lock_args: string;
    type_code_hash?: string;
    type_hash_type?: number;
    type_args?: string;
    data?: string;
  }[];
  cell_deps: {
    tx_hash: string;
    index: number;
    dep_type: number;
  }[];
  fee: number;
};

export type TrezorSignTxResult = {
  signature: `0x${string}`;
  txHash: `0x${string}`;
};

export type EstimateCyclesResult = {
  status: "ok";
  cycles: string;
};

export type EstimateCyclesError = {
  status: "error";
  message: string;
};

type CliArgs = {
  recipeFile?: string;
  caseName: string[];
  mnemonicFile?: string;
  network: Network;
  path: string;
  externalPath?: string;
  transport: string;
  trezorctl: string;
  hardwareSign: boolean;
  chunkify: boolean;
  outDir: string;
  outCaseFile: string;
  outRecipeFile: string;
  send: boolean;
  generateFixtureRecipes: boolean;
  fixtureName: string[];
  fromAddress?: string;
  toAddress?: string;
  help?: boolean;
};

export type FixtureRecipeBuildOptions = {
  mnemonic?: string;
  fromAddress?: string;
  externalAddress?: string;
  externalPath?: string;
  fixtureNames?: string[];
  network?: Network;
  path?: string;
  transport?: string;
};

class AddressOnlyCkbSigner extends ccc.Signer {
  constructor(
    client: ccc.Client,
    private readonly address: string,
  ) {
    super(client);
  }

  get type(): ccc.SignerType {
    return ccc.SignerType.CKB;
  }

  get signType(): ccc.SignerSignType {
    return ccc.SignerSignType.CkbSecp256k1;
  }

  async connect(): Promise<void> {}

  async isConnected(): Promise<boolean> {
    return true;
  }

  async getInternalAddress(): Promise<string> {
    return this.address;
  }

  async getAddressObjs(): Promise<ccc.Address[]> {
    return [await ccc.Address.fromString(this.address, this.client)];
  }

  async getRecommendedAddressObj(): Promise<ccc.Address> {
    return ccc.Address.fromString(this.address, this.client);
  }

  async prepareTransaction(txLike: ccc.TransactionLike): Promise<ccc.Transaction> {
    const tx = ccc.Transaction.from(txLike);
    const { script } = await this.getRecommendedAddressObj();
    await tx.addCellDepsOfKnownScripts(this.client, ccc.KnownScript.Secp256k1Blake160);
    await tx.prepareSighashAllWitness(script, 65, this.client);
    return tx;
  }

  async signOnlyTransaction(): Promise<ccc.Transaction> {
    throw new Error("AddressOnlyCkbSigner cannot sign; use trezorctl hardware signing");
  }
}

export function shannonsFromCkb(amount: string): bigint {
  const text = String(amount);
  if (!/^(0|[1-9]\d*)(\.\d+)?$/.test(text)) {
    throw new Error(`invalid CKB amount: ${text}`);
  }
  const [whole, fraction = ""] = text.split(".");
  if (fraction.length > 8) {
    throw new Error("CKB amount supports up to 8 decimals");
  }
  return BigInt(whole) * 100_000_000n + BigInt((fraction + "0".repeat(8)).slice(0, 8));
}

export function derivePrivateKeyFromMnemonic(
  mnemonic: string,
  derivationPath = DEFAULT_PATH,
): `0x${string}` {
  const seed = mnemonicToSeedSync(mnemonic.trim());
  const child = HDKey.fromMasterSeed(seed).derive(derivationPath);
  if (!child.privateKey) {
    throw new Error(`failed to derive private key for path ${derivationPath}`);
  }
  return `0x${Buffer.from(child.privateKey).toString("hex")}`;
}

export async function deriveAddressFromMnemonic(
  mnemonic: string,
  {
    network = "Testnet",
    derivationPath = DEFAULT_PATH,
  }: {
    network?: Network;
    derivationPath?: string;
  } = {},
): Promise<string> {
  const privateKey = derivePrivateKeyFromMnemonic(mnemonic, derivationPath);
  const client = createClient(network);
  const signer = new ccc.SignerCkbPrivateKey(client, privateKey);
  return signer.getRecommendedAddress();
}

export async function buildFixtureRecipePayloadFromOptions(
  options: FixtureRecipeBuildOptions,
): Promise<ReturnType<typeof buildOnchainFixtureRecipePayload>> {
  const network = options.network ?? "Testnet";
  const derivationPath = options.path ?? DEFAULT_PATH;
  const fromAddress =
    options.fromAddress ??
    (options.mnemonic
      ? await deriveAddressFromMnemonic(options.mnemonic, {
          network,
          derivationPath,
        })
      : undefined);
  if (!fromAddress) {
    throw new Error(
      "--from-address is required unless a mnemonic is provided via CKB_TEST_MNEMONIC or --mnemonic-file",
    );
  }
  const externalAddress =
    options.externalAddress ??
    (options.mnemonic && options.externalPath
      ? await deriveAddressFromMnemonic(options.mnemonic, {
          network,
          derivationPath: options.externalPath,
        })
      : undefined);
  return buildOnchainFixtureRecipePayload({
    fromAddress,
    externalAddress,
    externalPath: options.externalPath,
    fixtureNames: options.fixtureNames,
    network,
    path: derivationPath,
    transport: options.transport,
  });
}

function isNetwork(value: string): value is Network {
  return value === "Mainnet" || value === "Testnet";
}

function isSignaturePolicy(value: string): value is SignaturePolicy {
  return value === "ignore" || value === "compare" || value === "require";
}

function isRecipeKind(value: string): value is RecipeKind {
  return (
    value === "self_transfer" ||
    value === "transfer" ||
    value === "multi_output" ||
    value === "mixed_lock_groups" ||
    value === "custom_lock_output" ||
    value === "custom_type_outputs" ||
    value === "xudt_mint" ||
    value === "xudt_transfer" ||
    value === "dao_deposit" ||
    value === "dao_withdraw1" ||
    value === "two_stage_same_lock" ||
    value === "two_stage_witness_payload" ||
    value === "many_inputs_one_output" ||
    value === "two_stage_many_inputs_one_output"
  );
}

function normalizeHexData(value: string | undefined, context: string): `0x${string}` {
  const data = value ?? "0x";
  if (!/^0x([0-9a-fA-F]{2})*$/.test(data)) {
    throw new Error(`${context} must be 0x-prefixed even-length hex data`);
  }
  return data as `0x${string}`;
}

function normalizeHashType(value: string | undefined, context: string): ccc.HashType {
  try {
    return ccc.hashTypeFrom(value ?? "type");
  } catch (error: unknown) {
    throw new Error(
      `${context} must be a supported CKB hash type: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

function normalizeKnownScriptName(value: string, context: string): string {
  if (!(value in ccc.KnownScript)) {
    throw new Error(`${context} uses unsupported known script: ${value}`);
  }
  return value;
}

function normalizeNonNegativeInteger(value: string | undefined, context: string): bigint {
  const text = value ?? "0";
  if (!/^(0|[1-9]\d*)$/.test(text)) {
    throw new Error(`${context} must be a non-negative integer`);
  }
  return BigInt(text);
}

function normalizeRecipe(rawRecipe: RawRecipe, defaults: RawRecipe): NormalizedRecipe {
  const merged: RawRecipe = { ...defaults, ...rawRecipe };
  if (!merged.name) {
    throw new Error("recipe is missing required field: name");
  }
  if (!merged.kind) {
    throw new Error("recipe is missing required field: kind");
  }
  if (!isRecipeKind(merged.kind)) {
    throw new Error(`unsupported recipe kind for ${merged.name}: ${merged.kind}`);
  }

  const network = merged.network ?? "Testnet";
  if (!isNetwork(network)) {
    throw new Error(`unsupported network for recipe ${merged.name}: ${network}`);
  }

  const signaturePolicy = merged.signature_policy ?? "require";
  if (!isSignaturePolicy(signaturePolicy)) {
    throw new Error(
      `unsupported signature_policy for recipe ${merged.name}: ${signaturePolicy}`,
    );
  }
  if (!merged.from_address) {
    throw new Error(`recipe ${merged.name} requires from_address`);
  }

  const recipe: NormalizedRecipe = {
    name: merged.name,
    kind: merged.kind,
    network,
    fromAddress: merged.from_address,
    path: merged.path ?? DEFAULT_PATH,
    transport: merged.transport ?? "webusb:000:1",
    signaturePolicy,
    feeRate: Number(merged.fee_rate ?? DEFAULT_FEE_RATE),
    rpcUrl: merged.rpc_url,
    waitCommitted: Boolean(merged.wait_committed ?? true),
  };

  if (!Number.isSafeInteger(recipe.feeRate) || recipe.feeRate <= 0) {
    throw new Error(`recipe ${recipe.name} requires a positive integer fee_rate`);
  }
  if (merged.min_input_count !== undefined) {
    if (
      !Number.isSafeInteger(merged.min_input_count) ||
      merged.min_input_count < 0
    ) {
      throw new Error(`recipe ${recipe.name} requires a non-negative integer min_input_count`);
    }
    recipe.minInputCount = merged.min_input_count;
  }

  if (recipe.kind === "self_transfer") {
    recipe.toAddress = recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(
      merged.amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB,
    );
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    return recipe;
  }

  if (recipe.kind === "transfer") {
    if (!merged.to_address) {
      throw new Error(`recipe ${recipe.name} requires to_address`);
    }
    if (!merged.amount_ckb) {
      throw new Error(`recipe ${recipe.name} requires amount_ckb`);
    }
    recipe.toAddress = merged.to_address;
    recipe.amountShannons = shannonsFromCkb(merged.amount_ckb);
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    recipe.extraKnownCellDeps = (merged.extra_known_cell_deps ?? []).map((value) =>
      normalizeKnownScriptName(value, `recipe ${recipe.name} extra_known_cell_deps`),
    );
    return recipe;
  }

  if (recipe.kind === "custom_lock_output") {
    recipe.amountShannons = shannonsFromCkb(merged.amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB);
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    recipe.customLockHashType = normalizeHashType(
      merged.custom_lock_hash_type,
      `recipe ${recipe.name} custom_lock_hash_type`,
    );
    recipe.customLockArgs = normalizeHexData(
      merged.custom_lock_args,
      `recipe ${recipe.name} custom_lock_args`,
    );
    return recipe;
  }

  if (recipe.kind === "custom_type_outputs") {
    recipe.toAddress = merged.to_address ?? recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(merged.amount_ckb ?? "150");
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    const hashTypes = merged.custom_type_hash_types ?? ["data1"];
    if (!Array.isArray(hashTypes) || hashTypes.length === 0) {
      throw new Error(`recipe ${recipe.name} requires non-empty custom_type_hash_types`);
    }
    recipe.customTypeHashTypes = hashTypes.map((hashType) =>
      normalizeHashType(hashType, `recipe ${recipe.name} custom_type_hash_types`),
    );
    recipe.customTypeArgs = normalizeHexData(
      merged.custom_type_args,
      `recipe ${recipe.name} custom_type_args`,
    );
    return recipe;
  }

  if (recipe.kind === "mixed_lock_groups") {
    if (!merged.secondary_address) {
      throw new Error(`recipe ${recipe.name} requires secondary_address`);
    }
    recipe.toAddress = recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(
      merged.amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB,
    );
    recipe.secondaryAddress = merged.secondary_address;
    recipe.secondaryPath = merged.secondary_path ?? DEFAULT_EXTERNAL_PATH;
    recipe.secondaryAmountShannons = shannonsFromCkb(
      merged.secondary_amount_ckb ?? "124",
    );
    recipe.primaryInputCount = merged.primary_input_count ?? 2;
    recipe.secondaryInputCount = merged.secondary_input_count ?? 2;
    recipe.primaryWitnessInputType = normalizeHexData(
      merged.primary_witness_input_type,
      `recipe ${recipe.name} primary_witness_input_type`,
    );
    recipe.primaryWitnessOutputType = normalizeHexData(
      merged.primary_witness_output_type,
      `recipe ${recipe.name} primary_witness_output_type`,
    );
    recipe.secondaryWitnessInputType = normalizeHexData(
      merged.secondary_witness_input_type,
      `recipe ${recipe.name} secondary_witness_input_type`,
    );
    recipe.secondaryWitnessOutputType = normalizeHexData(
      merged.secondary_witness_output_type,
      `recipe ${recipe.name} secondary_witness_output_type`,
    );
    for (const [field, value] of [
      ["primary_input_count", recipe.primaryInputCount],
      ["secondary_input_count", recipe.secondaryInputCount],
    ] as const) {
      if (!Number.isSafeInteger(value) || value <= 0) {
        throw new Error(`recipe ${recipe.name} requires a positive integer ${field}`);
      }
    }
    return recipe;
  }

  if (recipe.kind === "xudt_mint") {
    recipe.toAddress = recipe.fromAddress;
    recipe.xudtAmount = normalizeNonNegativeInteger(
      merged.xudt_amount ?? "1000000",
      `recipe ${recipe.name} xudt_amount`,
    );
    if (recipe.xudtAmount <= 0n) {
      throw new Error(`recipe ${recipe.name} requires positive xudt_amount`);
    }
    recipe.xudtCellCapacityShannons = shannonsFromCkb(
      merged.xudt_cell_capacity_ckb ?? "150",
    );
    return recipe;
  }

  if (recipe.kind === "xudt_transfer") {
    if (!merged.to_address) {
      throw new Error(`recipe ${recipe.name} requires to_address`);
    }
    recipe.toAddress = merged.to_address;
    recipe.xudtAmount = normalizeNonNegativeInteger(
      merged.xudt_amount ?? "400000",
      `recipe ${recipe.name} xudt_amount`,
    );
    recipe.xudtChangeAmount = normalizeNonNegativeInteger(
      merged.xudt_change_amount ?? "600000",
      `recipe ${recipe.name} xudt_change_amount`,
    );
    if (recipe.xudtAmount <= 0n) {
      throw new Error(`recipe ${recipe.name} requires positive xudt_amount`);
    }
    recipe.xudtCellCapacityShannons = shannonsFromCkb(
      merged.xudt_cell_capacity_ckb ?? "150",
    );
    return recipe;
  }

  if (recipe.kind === "dao_deposit" || recipe.kind === "dao_withdraw1") {
    recipe.toAddress = recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(merged.amount_ckb ?? "102");
    return recipe;
  }

  if (recipe.kind === "two_stage_same_lock") {
    recipe.toAddress = recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(merged.amount_ckb ?? "123");
    recipe.fundingAmountShannons = shannonsFromCkb(
      merged.funding_amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB,
    );
    recipe.fundingOutputCount = 2;
    recipe.targetInputCount = 2;
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    return recipe;
  }

  if (recipe.kind === "two_stage_witness_payload") {
    recipe.toAddress = recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(merged.amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB);
    recipe.fundingAmountShannons = shannonsFromCkb(
      merged.funding_amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB,
    );
    recipe.fundingOutputCount = 2;
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    recipe.witnessInputType = normalizeHexData(
      merged.witness_input_type,
      `recipe ${recipe.name} witness_input_type`,
    );
    recipe.witnessOutputType = normalizeHexData(
      merged.witness_output_type,
      `recipe ${recipe.name} witness_output_type`,
    );
    recipe.trailingWitness = normalizeHexData(
      merged.trailing_witness,
      `recipe ${recipe.name} trailing_witness`,
    );
    recipe.sameGroupSecondWitness = normalizeHexData(
      merged.same_group_second_witness,
      `recipe ${recipe.name} same_group_second_witness`,
    );
    recipe.targetInputCount = merged.target_input_count ?? 1;
    if (!Number.isSafeInteger(recipe.targetInputCount) || recipe.targetInputCount <= 0) {
      throw new Error(`recipe ${recipe.name} requires a positive integer target_input_count`);
    }
    if (recipe.targetInputCount > 2) {
      throw new Error(`recipe ${recipe.name} supports at most two staged target inputs`);
    }
    return recipe;
  }

  if (recipe.kind === "two_stage_many_inputs_one_output") {
    recipe.toAddress = recipe.fromAddress;
    recipe.fundingAmountShannons = shannonsFromCkb(
      merged.funding_amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB,
    );
    recipe.fundingOutputCount = merged.funding_output_count ?? 50;
    if (!Number.isSafeInteger(recipe.fundingOutputCount) || recipe.fundingOutputCount <= 0) {
      throw new Error(`recipe ${recipe.name} requires a positive integer funding_output_count`);
    }
    recipe.targetInputCount = recipe.fundingOutputCount;
    recipe.amountShannons = recipe.fundingAmountShannons;
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    return recipe;
  }

  if (recipe.kind === "many_inputs_one_output") {
    recipe.toAddress = recipe.fromAddress;
    recipe.amountShannons = shannonsFromCkb(
      merged.amount_ckb ?? DEFAULT_SELF_TRANSFER_CKB,
    );
    recipe.outputData = normalizeHexData(merged.output_data, `recipe ${recipe.name} output_data`);
    return recipe;
  }

  if (!Array.isArray(merged.outputs) || merged.outputs.length === 0) {
    throw new Error(`recipe ${recipe.name} requires a non-empty outputs array`);
  }
  recipe.outputs = merged.outputs.map((output, index) => {
    if (!output.to_address || !output.amount_ckb) {
      throw new Error(
        `recipe ${recipe.name} output ${index} requires to_address and amount_ckb`,
      );
    }
    return {
      toAddress: output.to_address,
      amountShannons: shannonsFromCkb(output.amount_ckb),
      data: normalizeHexData(output.data, `recipe ${recipe.name} output ${index} data`),
    };
  });
  return recipe;
}

export function loadRecipesFromObject(payload: RecipePayload): NormalizedRecipe[] {
  const defaults = payload.defaults ?? {};
  const rawRecipes = payload.recipes;
  if (!Array.isArray(rawRecipes) || rawRecipes.length === 0) {
    throw new Error("recipe file must contain a non-empty recipes array");
  }

  const seenRawNames = new Set<string>();
  for (const rawRecipe of rawRecipes) {
    if (rawRecipe.name) {
      if (seenRawNames.has(rawRecipe.name)) {
        throw new Error(`duplicate recipe name: ${rawRecipe.name}`);
      }
      seenRawNames.add(rawRecipe.name);
    }
  }

  return rawRecipes.map((rawRecipe) => normalizeRecipe(rawRecipe, defaults));
}

export function loadRecipesFromFile(recipeFile: string): NormalizedRecipe[] {
  return loadRecipesFromObject(JSON.parse(fs.readFileSync(recipeFile, "utf8")) as RecipePayload);
}

export function buildCompareCases(
  recipes: NormalizedRecipe[],
  submitted: SubmittedTx[],
): unknown {
  if (recipes.length === 0) {
    throw new Error("cannot build compare cases without recipes");
  }
  const first = recipes[0];
  const submittedByName = new Map(submitted.map((entry) => [entry.name, entry]));
  const cases: Record<string, unknown>[] = [];
  for (let index = 0; index < recipes.length; index += 1) {
    const recipe = recipes[index];
    const entry = submittedByName.get(recipe.name) ?? submitted[index];
    if (!entry) {
      throw new Error(`missing submitted tx for recipe ${recipe.name}`);
    }
    if (recipe.kind === "mixed_lock_groups" && recipe.secondaryAddress && recipe.secondaryPath) {
      cases.push({
        name: `${recipe.name}-primary`,
        tx_hash: entry.txHash,
      });
      cases.push({
        name: `${recipe.name}-secondary`,
        address: recipe.secondaryAddress,
        path: recipe.secondaryPath,
        tx_hash: entry.txHash,
      });
      continue;
    }
    cases.push({
      name: entry.name,
      tx_hash: entry.txHash,
    });
  }

  return {
    defaults: {
      network: first.network,
      address: first.fromAddress,
      path: first.path,
      transport: first.transport,
      signature_policy: first.signaturePolicy,
    },
    cases,
  };
}

export function jsonReplacer(_key: string, value: unknown): unknown {
  return typeof value === "bigint" ? value.toString() : value;
}

export function sanitizeName(name: string): string {
  const sanitized = name.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "");
  if (!sanitized) {
    throw new Error("name must contain at least one safe character");
  }
  return sanitized;
}

function udtAmountData(amount: bigint): `0x${string}` {
  if (amount < 0n) {
    throw new Error("UDT amount must be non-negative");
  }
  return ccc.hexFrom(ccc.numLeToBytes(amount, 16)) as `0x${string}`;
}

function daoData(blockNumber: bigint): `0x${string}` {
  return ccc.hexFrom(ccc.numLeToBytes(blockNumber, 8)) as `0x${string}`;
}

function ensureParentDir(filePath: string): void {
  const dir = path.dirname(filePath);
  if (dir !== ".") {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function createClient(
  network: Network,
  rpcUrl?: string,
): ccc.ClientPublicTestnet | ccc.ClientPublicMainnet {
  if (network === "Testnet") {
    return new ccc.ClientPublicTestnet(rpcUrl ? { url: rpcUrl } : undefined);
  }
  return new ccc.ClientPublicMainnet(rpcUrl ? { url: rpcUrl } : undefined);
}

async function scriptFromAddress(address: string, client: ccc.Client): Promise<ccc.Script> {
  return (await ccc.Address.fromString(address, client)).script;
}

async function xudtTypeFromOwnerLock(
  ownerLock: ccc.Script,
  client: ccc.Client,
): Promise<ccc.Script> {
  return ccc.Script.fromKnownScript(client, ccc.KnownScript.XUdt, ownerLock.hash());
}

async function nervosDaoTypeScript(client: ccc.Client): Promise<ccc.Script> {
  return ccc.Script.fromKnownScript(client, ccc.KnownScript.NervosDao, "0x");
}

function knownScriptFromName(name: string): ccc.KnownScript {
  return ccc.KnownScript[name as keyof typeof ccc.KnownScript];
}

async function addExtraKnownCellDeps(
  tx: ccc.Transaction,
  client: ccc.Client,
  names?: string[],
): Promise<void> {
  if (!names || names.length === 0) {
    return;
  }
  await tx.addCellDepsOfKnownScripts(client, ...names.map(knownScriptFromName));
}

async function customLockScriptFromRecipe(
  recipe: NormalizedRecipe,
  client: ccc.Client,
): Promise<ccc.Script> {
  if (!recipe.customLockHashType || recipe.customLockArgs === undefined) {
    throw new Error(`recipe ${recipe.name} is missing custom lock fields`);
  }
  const secp = await client.getKnownScript(ccc.KnownScript.Secp256k1Blake160);
  return new ccc.Script(secp.codeHash, recipe.customLockHashType, recipe.customLockArgs);
}

async function alwaysSuccessTypeScript(
  hashType: ccc.HashType,
  args: `0x${string}`,
  client: ccc.Client,
): Promise<ccc.Script> {
  const alwaysSuccess = await client.getKnownScript(ccc.KnownScript.AlwaysSuccess);
  return new ccc.Script(alwaysSuccess.codeHash, hashType, args);
}

async function completeInputsToMinimumCount(
  tx: ccc.Transaction,
  signer: ccc.Signer,
  minInputCount?: number,
): Promise<void> {
  if (minInputCount === undefined || tx.inputs.length >= minInputCount) {
    return;
  }

  await tx.completeInputs(
    signer,
    {
      scriptLenRange: [0, 1],
      outputDataLenRange: [0, 1],
    },
    (_acc, _cell, _index, collectedCells) => {
      return tx.inputs.length + collectedCells.length >= minInputCount ? undefined : 0;
    },
    0,
  );

  if (tx.inputs.length < minInputCount) {
    throw new Error(
      `could not collect ${minInputCount} inputs for signer; only found ${tx.inputs.length}`,
    );
  }
}

async function addInputsFromSigner(
  tx: ccc.Transaction,
  signer: ccc.Signer,
  inputCount: number,
): Promise<void> {
  const beforeCount = tx.inputs.length;
  await tx.completeInputs(
    signer,
    {
      scriptLenRange: [0, 1],
      outputDataLenRange: [0, 1],
    },
    (_acc, _cell, _index, collectedCells) => {
      return collectedCells.length >= inputCount ? undefined : 0;
    },
    0,
  );

  const addedCount = tx.inputs.length - beforeCount;
  if (addedCount < inputCount) {
    throw new Error(
      `could not collect ${inputCount} inputs for signer; only found ${addedCount}`,
    );
  }
}

export async function buildTransactionFromRecipe(
  recipe: NormalizedRecipe,
  signer: ccc.Signer,
  client: ccc.Client,
): Promise<ccc.Transaction> {
  if (recipe.kind === "mixed_lock_groups") {
    throw new Error("mixed_lock_groups requires the dedicated multi-signer builder");
  }
  if (recipe.kind === "two_stage_same_lock") {
    throw new Error("two_stage_same_lock requires the dedicated two-stage builder");
  }
  if (recipe.kind === "two_stage_witness_payload") {
    throw new Error("two_stage_witness_payload requires the dedicated two-stage builder");
  }
  if (recipe.kind === "two_stage_many_inputs_one_output") {
    throw new Error("two_stage_many_inputs_one_output requires the dedicated two-stage builder");
  }
  if (recipe.kind === "xudt_transfer") {
    throw new Error("xudt_transfer requires the dedicated two-stage xUDT builder");
  }
  if (recipe.kind === "dao_withdraw1") {
    throw new Error("dao_withdraw1 requires the dedicated two-stage DAO builder");
  }

  const tx = ccc.Transaction.default();

  if (recipe.kind === "dao_deposit") {
    if (recipe.amountShannons === undefined) {
      throw new Error(`recipe ${recipe.name} is missing DAO deposit amount`);
    }
    const lock = await scriptFromAddress(recipe.fromAddress, client);
    const type = await nervosDaoTypeScript(client);
    await tx.addCellDepsOfKnownScripts(client, ccc.KnownScript.NervosDao);
    tx.addOutput({ capacity: recipe.amountShannons, lock, type }, daoData(0n));
    await tx.completeInputsByCapacity(signer);
    await tx.completeFeeBy(signer, BigInt(recipe.feeRate));
    return tx;
  }

  if (recipe.kind === "xudt_mint") {
    if (recipe.xudtAmount === undefined || recipe.xudtCellCapacityShannons === undefined) {
      throw new Error(`recipe ${recipe.name} is missing xUDT mint fields`);
    }
    const ownerLock = await scriptFromAddress(recipe.fromAddress, client);
    const type = await xudtTypeFromOwnerLock(ownerLock, client);
    await tx.addCellDepsOfKnownScripts(client, ccc.KnownScript.XUdt);
    tx.addOutput(
      { capacity: recipe.xudtCellCapacityShannons, lock: ownerLock, type },
      udtAmountData(recipe.xudtAmount),
    );
    await tx.completeInputsByCapacity(signer);
    await tx.completeFeeBy(signer, BigInt(recipe.feeRate));
    return tx;
  }

  if (recipe.kind === "custom_lock_output") {
    if (recipe.amountShannons === undefined) {
      throw new Error(`recipe ${recipe.name} is missing custom lock output amount`);
    }
    tx.addOutput(
      {
        capacity: recipe.amountShannons,
        lock: await customLockScriptFromRecipe(recipe, client),
      },
      recipe.outputData ?? "0x",
    );
  } else if (recipe.kind === "custom_type_outputs") {
    if (
      !recipe.toAddress ||
      recipe.amountShannons === undefined ||
      !recipe.customTypeHashTypes ||
      recipe.customTypeArgs === undefined
    ) {
      throw new Error(`recipe ${recipe.name} is missing custom type output fields`);
    }
    await tx.addCellDepsOfKnownScripts(client, ccc.KnownScript.AlwaysSuccess);
    const lock = await scriptFromAddress(recipe.toAddress, client);
    for (const hashType of recipe.customTypeHashTypes) {
      tx.addOutput(
        {
          capacity: recipe.amountShannons,
          lock,
          type: await alwaysSuccessTypeScript(hashType, recipe.customTypeArgs, client),
        },
        recipe.outputData ?? "0x",
      );
    }
  } else if (
    recipe.kind === "self_transfer" ||
    recipe.kind === "transfer" ||
    recipe.kind === "many_inputs_one_output"
  ) {
    if (!recipe.toAddress || recipe.amountShannons === undefined) {
      throw new Error(`recipe ${recipe.name} is missing normalized output`);
    }
    const lock = await scriptFromAddress(recipe.toAddress, client);
    tx.addOutput({ capacity: recipe.amountShannons, lock }, recipe.outputData ?? "0x");
  } else {
    if (!recipe.outputs) {
      throw new Error(`recipe ${recipe.name} is missing normalized outputs`);
    }
    for (const output of recipe.outputs) {
      const lock = await scriptFromAddress(output.toAddress, client);
      tx.addOutput({ capacity: output.amountShannons, lock }, output.data);
    }
  }

  await addExtraKnownCellDeps(tx, client, recipe.extraKnownCellDeps);
  await completeInputsToMinimumCount(tx, signer, recipe.minInputCount);
  await tx.completeInputsByCapacity(signer);
  if (recipe.minInputCount !== undefined) {
    padEmptyWitnessesToInputCount(tx);
  }
  if (recipe.kind === "many_inputs_one_output") {
    await tx.completeFeeChangeToOutput(signer, 0, BigInt(recipe.feeRate), undefined, {
      shouldAddInputs: false,
    });
    return tx;
  }
  await tx.completeFeeBy(signer, BigInt(recipe.feeRate));
  return tx;
}

async function buildTwoStageFundingTransactionFromRecipe(
  recipe: NormalizedRecipe,
  signer: ccc.Signer,
  client: ccc.Client,
): Promise<ccc.Transaction> {
  if (!recipe.fundingAmountShannons) {
    throw new Error(`recipe ${recipe.name} is missing funding amount`);
  }

  const lock = await scriptFromAddress(recipe.fromAddress, client);
  const tx = ccc.Transaction.default();
  const fundingOutputCount = recipe.fundingOutputCount ?? 2;
  for (let index = 0; index < fundingOutputCount; index += 1) {
    tx.addOutput({ capacity: recipe.fundingAmountShannons, lock }, "0x");
  }
  await tx.completeInputsByCapacity(signer);
  await tx.completeFeeBy(signer, BigInt(recipe.feeRate));
  return tx;
}

async function buildTwoStageTargetTransactionFromFunding(
  recipe: NormalizedRecipe,
  signer: ccc.Signer,
  client: ccc.Client,
  fundingTxHash: `0x${string}`,
  fundingTx: ccc.Transaction,
): Promise<ccc.Transaction> {
  if (recipe.amountShannons === undefined) {
    throw new Error(`recipe ${recipe.name} is missing target amount`);
  }
  const targetInputCount = recipe.targetInputCount ?? 2;
  if (fundingTx.outputs.length < targetInputCount) {
    throw new Error(
      `recipe ${recipe.name} funding transaction must have at least ${targetInputCount} outputs`,
    );
  }

  const lock = await scriptFromAddress(recipe.fromAddress, client);
  const tx = ccc.Transaction.default();
  const initialOutputCapacity =
    recipe.amountShannons ?? recipe.fundingAmountShannons ?? shannonsFromCkb(DEFAULT_SELF_TRANSFER_CKB);
  tx.addOutput({ capacity: initialOutputCapacity, lock }, recipe.outputData ?? "0x");
  for (let index = 0; index < targetInputCount; index += 1) {
    tx.addInput({
      outPoint: { txHash: fundingTxHash, index },
      cellOutput: fundingTx.outputs[index],
      outputData: fundingTx.outputsData[index] ?? "0x",
    });
  }
  const firstWitness = tx.getWitnessArgsAt(0) ?? ccc.WitnessArgs.from({});
  if (recipe.witnessInputType && recipe.witnessInputType !== "0x") {
    firstWitness.inputType = recipe.witnessInputType;
  }
  if (recipe.witnessOutputType && recipe.witnessOutputType !== "0x") {
    firstWitness.outputType = recipe.witnessOutputType;
  }
  if (firstWitness.inputType || firstWitness.outputType) {
    tx.setWitnessArgsAt(0, firstWitness);
  }
  if (recipe.sameGroupSecondWitness && recipe.sameGroupSecondWitness !== "0x") {
    if (targetInputCount < 2) {
      throw new Error(`recipe ${recipe.name} needs two inputs for same_group_second_witness`);
    }
    tx.setWitnessAt(1, recipe.sameGroupSecondWitness);
  }
  if (recipe.trailingWitness && recipe.trailingWitness !== "0x") {
    tx.setWitnessAt(targetInputCount, recipe.trailingWitness);
  }
  const prepared = await signer.prepareTransaction(tx);
  const inputCapacity = await prepared.getInputsCapacity(client);
  const estimatedFee = prepared.estimateFee(BigInt(recipe.feeRate));
  if (inputCapacity <= estimatedFee) {
    throw new Error(`recipe ${recipe.name} input capacity cannot cover estimated fee`);
  }
  prepared.outputs[0].capacity = inputCapacity - estimatedFee;
  return signer.prepareTransaction(prepared);
}

async function buildXudtTransferFromMintFunding(
  recipe: NormalizedRecipe,
  signer: ccc.Signer,
  client: ccc.Client,
  fundingTxHash: `0x${string}`,
  fundingTx: ccc.Transaction,
): Promise<ccc.Transaction> {
  if (
    recipe.xudtAmount === undefined ||
    recipe.xudtChangeAmount === undefined ||
    recipe.xudtCellCapacityShannons === undefined ||
    !recipe.toAddress
  ) {
    throw new Error(`recipe ${recipe.name} is missing xUDT transfer fields`);
  }
  if (fundingTx.outputs.length === 0 || !fundingTx.outputs[0].type) {
    throw new Error(`recipe ${recipe.name} xUDT funding transaction has no token output`);
  }

  const ownerLock = await scriptFromAddress(recipe.fromAddress, client);
  const recipientLock = await scriptFromAddress(recipe.toAddress, client);
  const type = fundingTx.outputs[0].type;
  const tx = ccc.Transaction.default();
  tx.addInput({
    outPoint: { txHash: fundingTxHash, index: 0 },
    cellOutput: fundingTx.outputs[0],
    outputData: fundingTx.outputsData[0] ?? "0x",
  });
  tx.addOutput(
    { capacity: recipe.xudtCellCapacityShannons, lock: recipientLock, type },
    udtAmountData(recipe.xudtAmount),
  );
  if (recipe.xudtChangeAmount > 0n) {
    tx.addOutput(
      { capacity: recipe.xudtCellCapacityShannons, lock: ownerLock, type },
      udtAmountData(recipe.xudtChangeAmount),
    );
  }

  await tx.addCellDepsOfKnownScripts(client, ccc.KnownScript.XUdt);
  await tx.completeInputsByCapacity(signer);
  await tx.completeFeeBy(signer, BigInt(recipe.feeRate));
  return tx;
}

async function prepareAndMaybeSubmitXudtTransferRecipe({
  recipe,
  mnemonic,
  send,
  outDir,
}: {
  recipe: NormalizedRecipe;
  mnemonic: string;
  send: boolean;
  outDir: string;
}): Promise<PrepareResult> {
  const privateKey = derivePrivateKeyFromMnemonic(mnemonic, recipe.path);
  const client = createClient(recipe.network, recipe.rpcUrl);
  const signer = new ccc.SignerCkbPrivateKey(client, privateKey);
  const signerAddress = await signer.getRecommendedAddress();
  if (signerAddress !== recipe.fromAddress) {
    throw new Error(
      `mnemonic/path address mismatch for ${recipe.name}: derived ${signerAddress}, recipe expects ${recipe.fromAddress}`,
    );
  }

  const recipeDir = path.join(outDir, sanitizeName(recipe.name));
  const fundingDir = path.join(recipeDir, "mint-funding");
  const targetDir = path.join(recipeDir, "target");
  fs.mkdirSync(fundingDir, { recursive: true });
  fs.mkdirSync(targetDir, { recursive: true });
  fs.writeFileSync(
    path.join(recipeDir, "recipe.normalized.json"),
    `${JSON.stringify(recipe, jsonReplacer, 2)}\n`,
  );

  const mintRecipe: NormalizedRecipe = {
    ...recipe,
    name: `${recipe.name}-mint-funding`,
    kind: "xudt_mint",
    toAddress: recipe.fromAddress,
    xudtAmount: (recipe.xudtAmount ?? 0n) + (recipe.xudtChangeAmount ?? 0n),
  };
  const fundingTx = await buildTransactionFromRecipe(mintRecipe, signer, client);
  const signedFundingTx = await signer.signTransaction(fundingTx);
  fs.writeFileSync(
    path.join(fundingDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(fundingTx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(fundingDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedFundingTx, jsonReplacer, 2)}\n`,
  );

  if (send) {
    await estimateCyclesBeforeSend(
      client,
      signedFundingTx,
      path.join(fundingDir, "estimate_cycles.result.json"),
    );
  }

  if (!send) {
    return { name: recipe.name, txHash: null, status: "not_sent" };
  }

  const fundingTxHash = (await client.sendTransaction(signedFundingTx)) as `0x${string}`;
  fs.writeFileSync(
    path.join(fundingDir, "submit.result.json"),
    `${JSON.stringify({ name: `${recipe.name}-mint-funding`, txHash: fundingTxHash, status: "sent" }, jsonReplacer, 2)}\n`,
  );
  if (recipe.waitCommitted) {
    const committedFunding = await client.waitTransaction(
      fundingTxHash,
      0,
      WAIT_TRANSACTION_TIMEOUT_MS,
    );
    fs.writeFileSync(
      path.join(fundingDir, "committed.transaction.json"),
      `${JSON.stringify(committedFunding, jsonReplacer, 2)}\n`,
    );
  }

  const targetTx = await buildXudtTransferFromMintFunding(
    recipe,
    signer,
    client,
    fundingTxHash,
    signedFundingTx,
  );
  const signedTargetTx = await signer.signTransaction(targetTx);
  fs.writeFileSync(
    path.join(targetDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(targetTx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(targetDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedTargetTx, jsonReplacer, 2)}\n`,
  );
  await estimateCyclesBeforeSend(
    client,
    signedTargetTx,
    path.join(targetDir, "estimate_cycles.result.json"),
  );
  const targetTxHash = await client.sendTransaction(signedTargetTx);
  const result: PrepareResult = { name: recipe.name, txHash: targetTxHash, status: "sent" };
  fs.writeFileSync(
    path.join(targetDir, "submit.result.json"),
    `${JSON.stringify(result, jsonReplacer, 2)}\n`,
  );

  if (recipe.waitCommitted) {
    const committedTarget = await client.waitTransaction(
      targetTxHash,
      0,
      WAIT_TRANSACTION_TIMEOUT_MS,
    );
    fs.writeFileSync(
      path.join(targetDir, "committed.transaction.json"),
      `${JSON.stringify(committedTarget, jsonReplacer, 2)}\n`,
    );
  }

  return result;
}

async function buildDaoWithdraw1FromDepositFunding(
  recipe: NormalizedRecipe,
  signer: ccc.Signer,
  client: ccc.Client,
  depositTxHash: `0x${string}`,
  depositTx: ccc.Transaction,
): Promise<ccc.Transaction> {
  if (recipe.amountShannons === undefined) {
    throw new Error(`recipe ${recipe.name} is missing DAO withdraw1 amount`);
  }
  if (depositTx.outputs.length === 0 || !depositTx.outputs[0].type) {
    throw new Error(`recipe ${recipe.name} DAO deposit funding transaction has no DAO output`);
  }

  const depositOutPoint = { txHash: depositTxHash, index: 0 };
  const depositCellWithHeader = await client.getCellWithHeader(depositOutPoint);
  if (!depositCellWithHeader?.header) {
    throw new Error(`recipe ${recipe.name} cannot resolve committed DAO deposit header`);
  }

  const tx = ccc.Transaction.default();
  tx.headerDeps.push(depositCellWithHeader.header.hash);
  tx.addInput({
    outPoint: depositOutPoint,
    cellOutput: depositTx.outputs[0],
    outputData: depositTx.outputsData[0] ?? "0x",
  });
  tx.addOutput(
    {
      capacity: recipe.amountShannons,
      lock: depositTx.outputs[0].lock,
      type: depositTx.outputs[0].type,
    },
    daoData(depositCellWithHeader.header.number),
  );

  await tx.addCellDepsOfKnownScripts(client, ccc.KnownScript.NervosDao);
  await tx.completeInputsByCapacity(signer);
  await tx.completeFeeBy(signer, BigInt(recipe.feeRate));
  return tx;
}

async function prepareAndMaybeSubmitDaoWithdraw1Recipe({
  recipe,
  mnemonic,
  send,
  outDir,
}: {
  recipe: NormalizedRecipe;
  mnemonic: string;
  send: boolean;
  outDir: string;
}): Promise<PrepareResult> {
  const privateKey = derivePrivateKeyFromMnemonic(mnemonic, recipe.path);
  const client = createClient(recipe.network, recipe.rpcUrl);
  const signer = new ccc.SignerCkbPrivateKey(client, privateKey);
  const signerAddress = await signer.getRecommendedAddress();
  if (signerAddress !== recipe.fromAddress) {
    throw new Error(
      `mnemonic/path address mismatch for ${recipe.name}: derived ${signerAddress}, recipe expects ${recipe.fromAddress}`,
    );
  }

  const recipeDir = path.join(outDir, sanitizeName(recipe.name));
  const depositDir = path.join(recipeDir, "deposit-funding");
  const targetDir = path.join(recipeDir, "target");
  fs.mkdirSync(depositDir, { recursive: true });
  fs.mkdirSync(targetDir, { recursive: true });
  fs.writeFileSync(
    path.join(recipeDir, "recipe.normalized.json"),
    `${JSON.stringify(recipe, jsonReplacer, 2)}\n`,
  );

  const depositRecipe: NormalizedRecipe = {
    ...recipe,
    name: `${recipe.name}-deposit-funding`,
    kind: "dao_deposit",
    toAddress: recipe.fromAddress,
  };
  const depositTx = await buildTransactionFromRecipe(depositRecipe, signer, client);
  const signedDepositTx = await signer.signTransaction(depositTx);
  fs.writeFileSync(
    path.join(depositDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(depositTx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(depositDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedDepositTx, jsonReplacer, 2)}\n`,
  );

  if (send) {
    await estimateCyclesBeforeSend(
      client,
      signedDepositTx,
      path.join(depositDir, "estimate_cycles.result.json"),
    );
  }

  if (!send) {
    return { name: recipe.name, txHash: null, status: "not_sent" };
  }

  const depositTxHash = (await client.sendTransaction(signedDepositTx)) as `0x${string}`;
  fs.writeFileSync(
    path.join(depositDir, "submit.result.json"),
    `${JSON.stringify({ name: `${recipe.name}-deposit-funding`, txHash: depositTxHash, status: "sent" }, jsonReplacer, 2)}\n`,
  );
  if (recipe.waitCommitted) {
    const committedDeposit = await client.waitTransaction(
      depositTxHash,
      0,
      WAIT_TRANSACTION_TIMEOUT_MS,
    );
    fs.writeFileSync(
      path.join(depositDir, "committed.transaction.json"),
      `${JSON.stringify(committedDeposit, jsonReplacer, 2)}\n`,
    );
  }

  const targetTx = await buildDaoWithdraw1FromDepositFunding(
    recipe,
    signer,
    client,
    depositTxHash,
    signedDepositTx,
  );
  const signedTargetTx = await signer.signTransaction(targetTx);
  fs.writeFileSync(
    path.join(targetDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(targetTx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(targetDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedTargetTx, jsonReplacer, 2)}\n`,
  );
  await estimateCyclesBeforeSend(
    client,
    signedTargetTx,
    path.join(targetDir, "estimate_cycles.result.json"),
  );
  const targetTxHash = await client.sendTransaction(signedTargetTx);
  const result: PrepareResult = { name: recipe.name, txHash: targetTxHash, status: "sent" };
  fs.writeFileSync(
    path.join(targetDir, "submit.result.json"),
    `${JSON.stringify(result, jsonReplacer, 2)}\n`,
  );

  if (recipe.waitCommitted) {
    const committedTarget = await client.waitTransaction(
      targetTxHash,
      0,
      WAIT_TRANSACTION_TIMEOUT_MS,
    );
    fs.writeFileSync(
      path.join(targetDir, "committed.transaction.json"),
      `${JSON.stringify(committedTarget, jsonReplacer, 2)}\n`,
    );
  }

  return result;
}

async function buildMixedLockGroupsTransactionFromRecipe(
  recipe: NormalizedRecipe,
  primarySigner: ccc.SignerCkbPrivateKey,
  secondarySigner: ccc.SignerCkbPrivateKey,
  client: ccc.Client,
): Promise<ccc.Transaction> {
  if (
    !recipe.toAddress ||
    recipe.amountShannons === undefined ||
    !recipe.secondaryAddress ||
    recipe.secondaryAmountShannons === undefined ||
    recipe.primaryInputCount === undefined ||
    recipe.secondaryInputCount === undefined
  ) {
    throw new Error(`recipe ${recipe.name} is missing mixed lock group fields`);
  }

  const tx = ccc.Transaction.default();
  tx.addOutput(
    {
      capacity: recipe.amountShannons,
      lock: await scriptFromAddress(recipe.toAddress, client),
    },
    "0x",
  );
  tx.addOutput(
    {
      capacity: recipe.secondaryAmountShannons,
      lock: await scriptFromAddress(recipe.secondaryAddress, client),
    },
    "0x",
  );

  await addInputsFromSigner(tx, primarySigner, recipe.primaryInputCount);
  await addInputsFromSigner(tx, secondarySigner, recipe.secondaryInputCount);

  const primaryPrepared = await primarySigner.prepareTransaction(tx);
  const fullyPrepared = await secondarySigner.prepareTransaction(primaryPrepared);
  padEmptyWitnessesToInputCount(fullyPrepared);
  setWitnessPayloadAt(
    fullyPrepared,
    0,
    recipe.primaryWitnessInputType,
    recipe.primaryWitnessOutputType,
  );
  setWitnessPayloadAt(
    fullyPrepared,
    recipe.primaryInputCount,
    recipe.secondaryWitnessInputType,
    recipe.secondaryWitnessOutputType,
  );
  await fullyPrepared.completeFeeBy(primarySigner, BigInt(recipe.feeRate));

  return fullyPrepared;
}

export async function estimateCyclesBeforeSend(
  client: ccc.Client,
  tx: ccc.Transaction,
  artifactFile?: string,
): Promise<EstimateCyclesResult> {
  try {
    const cycles = await client.estimateCycles(tx);
    const result: EstimateCyclesResult = {
      status: "ok",
      cycles: cycles.toString(),
    };
    if (artifactFile) {
      fs.writeFileSync(artifactFile, `${JSON.stringify(result, null, 2)}\n`);
    }
    return result;
  } catch (error: unknown) {
    const result: EstimateCyclesError = {
      status: "error",
      message: error instanceof Error ? error.message : String(error),
    };
    if (artifactFile) {
      fs.writeFileSync(artifactFile, `${JSON.stringify(result, null, 2)}\n`);
    }
    throw new Error(`estimate_cycles failed: ${result.message}`);
  }
}

function safeJsonNumber(value: bigint, context: string): number {
  if (value > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error(`${context} exceeds JavaScript safe integer range: ${value}`);
  }
  return Number(value);
}

function hashTypeToTrezor(hashType: ccc.HashTypeLike): number {
  return ccc.hashTypeToBytes(hashType)[0] ?? 0;
}

function depTypeToTrezor(depType: ccc.DepTypeLike): number {
  return ccc.depTypeToBytes(depType)[0] ?? 0;
}

function normalizeTrezorHex(value: string): `0x${string}` {
  return value.startsWith("0x") ? (value as `0x${string}`) : `0x${value}`;
}

export async function buildTrezorSignTxJsonFromTransaction(
  tx: ccc.Transaction,
  client: ccc.Client,
): Promise<TrezorSignTxJson> {
  const fee = await tx.getFee(client);
  return {
    inputs: tx.inputs.map((input) => ({
      tx_hash: input.previousOutput.txHash,
      index: safeJsonNumber(input.previousOutput.index, "input index"),
      since: safeJsonNumber(input.since, "input since"),
    })),
    outputs: tx.outputs.map((output, index) => {
      const item: TrezorSignTxJson["outputs"][number] = {
        capacity: safeJsonNumber(output.capacity, `output ${index} capacity`),
        lock_code_hash: output.lock.codeHash,
        lock_hash_type: hashTypeToTrezor(output.lock.hashType),
        lock_args: output.lock.args,
        data: tx.outputsData[index] ?? "0x",
      };
      if (output.type) {
        item.type_code_hash = output.type.codeHash;
        item.type_hash_type = hashTypeToTrezor(output.type.hashType);
        item.type_args = output.type.args;
      }
      return item;
    }),
    cell_deps: tx.cellDeps.map((dep) => ({
      tx_hash: dep.outPoint.txHash,
      index: safeJsonNumber(dep.outPoint.index, "cell_dep index"),
      dep_type: depTypeToTrezor(dep.depType),
    })),
    fee: safeJsonNumber(fee, "transaction fee"),
  };
}

export function parseTrezorctlSignTxOutput(output: string): TrezorSignTxResult {
  const signature = output.match(/Signature:\s*(0x[0-9a-fA-F]{130})/);
  const txHash = output.match(/TX Hash:\s*(0x[0-9a-fA-F]{64})/);
  if (!signature || !txHash) {
    throw new Error("trezorctl output did not contain Signature and TX Hash");
  }
  return {
    signature: signature[1].toLowerCase() as `0x${string}`,
    txHash: txHash[1].toLowerCase() as `0x${string}`,
  };
}

export function applyTrezorSignatureToTransaction(
  tx: ccc.Transaction,
  signature: `0x${string}`,
  witnessIndex = 0,
): void {
  if (!/^0x[0-9a-fA-F]{130}$/.test(signature)) {
    throw new Error("CKB secp256k1_blake160 signature must be 65 bytes");
  }
  const witness = tx.getWitnessArgsAt(witnessIndex) ?? ccc.WitnessArgs.from({});
  witness.lock = normalizeTrezorHex(signature);
  tx.setWitnessArgsAt(witnessIndex, witness);
}

function padEmptyWitnessesToInputCount(tx: ccc.Transaction): void {
  for (let i = 0; i < tx.inputs.length; i += 1) {
    if (tx.witnesses[i] === undefined) {
      tx.setWitnessAt(i, "0x");
    }
  }
}

function setWitnessPayloadAt(
  tx: ccc.Transaction,
  witnessIndex: number,
  inputType?: `0x${string}`,
  outputType?: `0x${string}`,
): void {
  const hasInputType = inputType !== undefined && inputType !== "0x";
  const hasOutputType = outputType !== undefined && outputType !== "0x";
  if (!hasInputType && !hasOutputType) {
    return;
  }
  const witness = tx.getWitnessArgsAt(witnessIndex) ?? ccc.WitnessArgs.from({});
  if (hasInputType) {
    witness.inputType = inputType;
  }
  if (hasOutputType) {
    witness.outputType = outputType;
  }
  tx.setWitnessArgsAt(witnessIndex, witness);
}

function buildTrezorctlSignTxCommand({
  trezorctl,
  transport,
  network,
  path: derivationPath,
  jsonFile,
  chunkify,
}: {
  trezorctl: string;
  transport: string;
  network: Network;
  path: string;
  jsonFile: string;
  chunkify: boolean;
}): string[] {
  const command = [trezorctl];
  if (transport !== "auto") {
    command.push("-p", transport);
  }
  command.push("ckb", "sign-tx", "--coin", network, "-n", derivationPath);
  if (chunkify) {
    command.push("-C");
  }
  command.push(jsonFile);
  return command;
}

function buildTrezorctlGetAddressCommand({
  trezorctl,
  transport,
  network,
  path: derivationPath,
}: {
  trezorctl: string;
  transport: string;
  network: Network;
  path: string;
}): string[] {
  const command = [trezorctl];
  if (transport !== "auto") {
    command.push("-p", transport);
  }
  command.push("ckb", "get-address", "--coin", network, "-n", derivationPath);
  return command;
}

export function parseTrezorctlGetAddressOutput(output: string): string {
  const match = output.match(/\b(?:ckt1|ckb1)[0-9a-z]+\b/i);
  if (!match) {
    throw new Error("trezorctl output did not contain a CKB address");
  }
  return match[0];
}

function runTrezorctlGetAddress(command: string[]): string {
  const [executable, ...args] = command;
  const result = spawnSync(executable, args, {
    encoding: "utf8",
  });
  const stdout = result.stdout ?? "";
  const stderr = result.stderr ?? "";
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(
      `trezorctl get-address failed with exit code ${result.status}\n${stderr || stdout}`,
    );
  }
  return parseTrezorctlGetAddressOutput(`${stdout}\n${stderr}`);
}

function runTrezorctlSignTx(command: string[]): TrezorSignTxResult & {
  stdout: string;
  stderr: string;
  returnCode: number | null;
} {
  const [executable, ...args] = command;
  const result = spawnSync(executable, args, {
    encoding: "utf8",
  });
  const stdout = result.stdout ?? "";
  const stderr = result.stderr ?? "";
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(
      `trezorctl sign-tx failed with exit code ${result.status}\n${stderr || stdout}`,
    );
  }
  return {
    ...parseTrezorctlSignTxOutput(`${stdout}\n${stderr}`),
    stdout,
    stderr,
    returnCode: result.status,
  };
}

export async function prepareAndMaybeSubmitRecipeWithHardware({
  recipe,
  send,
  outDir,
  trezorctl,
  chunkify,
}: {
  recipe: NormalizedRecipe;
  send: boolean;
  outDir: string;
  trezorctl: string;
  chunkify: boolean;
}): Promise<PrepareResult> {
  if (recipe.kind === "mixed_lock_groups") {
    throw new Error("mixed_lock_groups cannot be signed by the current single-path trezorctl flow");
  }
  if (recipe.kind === "two_stage_same_lock") {
    throw new Error("two_stage_same_lock hardware generation is not supported; use mnemonic signing");
  }
  if (recipe.kind === "two_stage_witness_payload") {
    throw new Error("two_stage_witness_payload hardware generation is not supported; use mnemonic signing");
  }
  if (recipe.kind === "two_stage_many_inputs_one_output") {
    throw new Error("two_stage_many_inputs_one_output hardware generation is not supported; use mnemonic signing");
  }
  if (recipe.kind === "xudt_transfer") {
    throw new Error("xudt_transfer hardware generation is not supported; use mnemonic signing");
  }
  if (recipe.kind === "dao_withdraw1") {
    throw new Error("dao_withdraw1 hardware generation is not supported; use mnemonic signing");
  }

  const client = createClient(recipe.network, recipe.rpcUrl);
  const signer = new AddressOnlyCkbSigner(client, recipe.fromAddress);
  const tx = await buildTransactionFromRecipe(recipe, signer, client);
  padEmptyWitnessesToInputCount(tx);
  const trezorJson = await buildTrezorSignTxJsonFromTransaction(tx, client);
  const recipeDir = path.join(outDir, sanitizeName(recipe.name));
  fs.mkdirSync(recipeDir, { recursive: true });

  const trezorJsonFile = path.join(recipeDir, "trezor.sign_tx.json");
  fs.writeFileSync(
    path.join(recipeDir, "recipe.normalized.json"),
    `${JSON.stringify(recipe, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(recipeDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(tx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(trezorJsonFile, `${JSON.stringify(trezorJson, null, 2)}\n`);

  const command = buildTrezorctlSignTxCommand({
    trezorctl,
    transport: recipe.transport,
    network: recipe.network,
    path: recipe.path,
    jsonFile: trezorJsonFile,
    chunkify,
  });
  fs.writeFileSync(
    path.join(recipeDir, "trezorctl.command.json"),
    `${JSON.stringify(
      {
        operation: "ckb sign-tx",
        command,
      },
      null,
      2,
    )}\n`,
  );

  if (!send) {
    return { name: recipe.name, txHash: null, status: "not_sent" };
  }

  const signResult = runTrezorctlSignTx(command);
  fs.writeFileSync(
    path.join(recipeDir, "trezorctl.output.txt"),
    `${signResult.stdout}${signResult.stderr}`,
  );
  fs.writeFileSync(
    path.join(recipeDir, "trezor.sign_result.json"),
    `${JSON.stringify(signResult, null, 2)}\n`,
  );
  applyTrezorSignatureToTransaction(tx, signResult.signature);
  padEmptyWitnessesToInputCount(tx);
  fs.writeFileSync(
    path.join(recipeDir, "ccc.signed_tx.json"),
    `${JSON.stringify(tx, jsonReplacer, 2)}\n`,
  );

  await estimateCyclesBeforeSend(
    client,
    tx,
    path.join(recipeDir, "estimate_cycles.result.json"),
  );

  const txHash = await client.sendTransaction(tx);
  const result: PrepareResult = { name: recipe.name, txHash, status: "sent" };
  fs.writeFileSync(
    path.join(recipeDir, "submit.result.json"),
    `${JSON.stringify(result, jsonReplacer, 2)}\n`,
  );

  if (txHash.toLowerCase() !== signResult.txHash.toLowerCase()) {
    throw new Error(
      `broadcast tx hash mismatch for ${recipe.name}: trezor ${signResult.txHash}, node ${txHash}`,
    );
  }

  if (recipe.waitCommitted) {
    const committed = await client.waitTransaction(txHash, 0, WAIT_TRANSACTION_TIMEOUT_MS);
    fs.writeFileSync(
      path.join(recipeDir, "committed.transaction.json"),
      `${JSON.stringify(committed, jsonReplacer, 2)}\n`,
    );
  }

  return result;
}

async function prepareAndMaybeSubmitTwoStageSameLockRecipe({
  recipe,
  mnemonic,
  send,
  outDir,
}: {
  recipe: NormalizedRecipe;
  mnemonic: string;
  send: boolean;
  outDir: string;
}): Promise<PrepareResult> {
  const privateKey = derivePrivateKeyFromMnemonic(mnemonic, recipe.path);
  const client = createClient(recipe.network, recipe.rpcUrl);
  const signer = new ccc.SignerCkbPrivateKey(client, privateKey);
  const signerAddress = await signer.getRecommendedAddress();
  if (signerAddress !== recipe.fromAddress) {
    throw new Error(
      `mnemonic/path address mismatch for ${recipe.name}: derived ${signerAddress}, recipe expects ${recipe.fromAddress}`,
    );
  }

  const recipeDir = path.join(outDir, sanitizeName(recipe.name));
  const fundingDir = path.join(recipeDir, "funding");
  const targetDir = path.join(recipeDir, "target");
  fs.mkdirSync(fundingDir, { recursive: true });
  fs.mkdirSync(targetDir, { recursive: true });
  fs.writeFileSync(
    path.join(recipeDir, "recipe.normalized.json"),
    `${JSON.stringify(recipe, jsonReplacer, 2)}\n`,
  );

  const fundingTx = await buildTwoStageFundingTransactionFromRecipe(recipe, signer, client);
  const signedFundingTx = await signer.signTransaction(fundingTx);
  fs.writeFileSync(
    path.join(fundingDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(fundingTx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(fundingDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedFundingTx, jsonReplacer, 2)}\n`,
  );

  if (send) {
    await estimateCyclesBeforeSend(
      client,
      signedFundingTx,
      path.join(fundingDir, "estimate_cycles.result.json"),
    );
  }

  if (!send) {
    return { name: recipe.name, txHash: null, status: "not_sent" };
  }

  const fundingTxHash = (await client.sendTransaction(signedFundingTx)) as `0x${string}`;
  fs.writeFileSync(
    path.join(fundingDir, "submit.result.json"),
    `${JSON.stringify({ name: `${recipe.name}-funding`, txHash: fundingTxHash, status: "sent" }, jsonReplacer, 2)}\n`,
  );
  if (recipe.waitCommitted) {
    const committedFunding = await client.waitTransaction(
      fundingTxHash,
      0,
      WAIT_TRANSACTION_TIMEOUT_MS,
    );
    fs.writeFileSync(
      path.join(fundingDir, "committed.transaction.json"),
      `${JSON.stringify(committedFunding, jsonReplacer, 2)}\n`,
    );
  }

  const targetTx = await buildTwoStageTargetTransactionFromFunding(
    recipe,
    signer,
    client,
    fundingTxHash,
    signedFundingTx,
  );
  const signedTargetTx = await signer.signTransaction(targetTx);
  fs.writeFileSync(
    path.join(targetDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(targetTx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(targetDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedTargetTx, jsonReplacer, 2)}\n`,
  );
  await estimateCyclesBeforeSend(
    client,
    signedTargetTx,
    path.join(targetDir, "estimate_cycles.result.json"),
  );
  const targetTxHash = await client.sendTransaction(signedTargetTx);
  const result: PrepareResult = { name: recipe.name, txHash: targetTxHash, status: "sent" };
  fs.writeFileSync(
    path.join(targetDir, "submit.result.json"),
    `${JSON.stringify(result, jsonReplacer, 2)}\n`,
  );

  if (recipe.waitCommitted) {
    const committedTarget = await client.waitTransaction(
      targetTxHash,
      0,
      WAIT_TRANSACTION_TIMEOUT_MS,
    );
    fs.writeFileSync(
      path.join(targetDir, "committed.transaction.json"),
      `${JSON.stringify(committedTarget, jsonReplacer, 2)}\n`,
    );
  }

  return result;
}

export async function prepareAndMaybeSubmitRecipe({
  recipe,
  mnemonic,
  send,
  outDir,
}: {
  recipe: NormalizedRecipe;
  mnemonic: string;
  send: boolean;
  outDir: string;
}): Promise<PrepareResult> {
  if (
    recipe.kind === "two_stage_same_lock" ||
    recipe.kind === "two_stage_witness_payload" ||
    recipe.kind === "two_stage_many_inputs_one_output"
  ) {
    return prepareAndMaybeSubmitTwoStageSameLockRecipe({
      recipe,
      mnemonic,
      send,
      outDir,
    });
  }
  if (recipe.kind === "xudt_transfer") {
    return prepareAndMaybeSubmitXudtTransferRecipe({
      recipe,
      mnemonic,
      send,
      outDir,
    });
  }
  if (recipe.kind === "dao_withdraw1") {
    return prepareAndMaybeSubmitDaoWithdraw1Recipe({
      recipe,
      mnemonic,
      send,
      outDir,
    });
  }

  const privateKey = derivePrivateKeyFromMnemonic(mnemonic, recipe.path);
  const client = createClient(recipe.network, recipe.rpcUrl);
  const signer = new ccc.SignerCkbPrivateKey(client, privateKey);
  const signerAddress = await signer.getRecommendedAddress();
  if (signerAddress !== recipe.fromAddress) {
    throw new Error(
      `mnemonic/path address mismatch for ${recipe.name}: derived ${signerAddress}, recipe expects ${recipe.fromAddress}`,
    );
  }

  let tx: ccc.Transaction;
  let signedTx: ccc.Transaction;
  if (recipe.kind === "mixed_lock_groups") {
    if (!recipe.secondaryPath || !recipe.secondaryAddress) {
      throw new Error(`recipe ${recipe.name} is missing secondary path/address`);
    }
    const secondaryPrivateKey = derivePrivateKeyFromMnemonic(
      mnemonic,
      recipe.secondaryPath,
    );
    const secondarySigner = new ccc.SignerCkbPrivateKey(client, secondaryPrivateKey);
    const secondaryAddress = await secondarySigner.getRecommendedAddress();
    if (secondaryAddress !== recipe.secondaryAddress) {
      throw new Error(
        `mnemonic/secondary path address mismatch for ${recipe.name}: derived ${secondaryAddress}, recipe expects ${recipe.secondaryAddress}`,
      );
    }
    tx = await buildMixedLockGroupsTransactionFromRecipe(
      recipe,
      signer,
      secondarySigner,
      client,
    );
    const secondarySignedTx = await secondarySigner.signOnlyTransaction(tx);
    signedTx = await signer.signOnlyTransaction(secondarySignedTx);
  } else {
    tx = await buildTransactionFromRecipe(recipe, signer, client);
    signedTx = await signer.signTransaction(tx);
  }
  const recipeDir = path.join(outDir, sanitizeName(recipe.name));
  fs.mkdirSync(recipeDir, { recursive: true });
  fs.writeFileSync(
    path.join(recipeDir, "recipe.normalized.json"),
    `${JSON.stringify(recipe, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(recipeDir, "ccc.unsigned_tx.json"),
    `${JSON.stringify(tx, jsonReplacer, 2)}\n`,
  );
  fs.writeFileSync(
    path.join(recipeDir, "ccc.signed_tx.json"),
    `${JSON.stringify(signedTx, jsonReplacer, 2)}\n`,
  );

  if (send) {
    await estimateCyclesBeforeSend(
      client,
      signedTx,
      path.join(recipeDir, "estimate_cycles.result.json"),
    );
  }

  if (!send) {
    return { name: recipe.name, txHash: null, status: "not_sent" };
  }

  const txHash = await client.sendTransaction(signedTx);
  const result: PrepareResult = { name: recipe.name, txHash, status: "sent" };
  fs.writeFileSync(
    path.join(recipeDir, "submit.result.json"),
    `${JSON.stringify(result, jsonReplacer, 2)}\n`,
  );

  if (recipe.waitCommitted) {
    const committed = await client.waitTransaction(txHash, 0, WAIT_TRANSACTION_TIMEOUT_MS);
    fs.writeFileSync(
      path.join(recipeDir, "committed.transaction.json"),
      `${JSON.stringify(committed, jsonReplacer, 2)}\n`,
    );
  }

  return result;
}

function readMnemonic({ mnemonicFile }: { mnemonicFile?: string }): string {
  if (mnemonicFile) {
    return fs.readFileSync(mnemonicFile, "utf8").trim();
  }
  const mnemonic = process.env.CKB_TEST_MNEMONIC;
  if (!mnemonic) {
    throw new Error("set CKB_TEST_MNEMONIC or pass --mnemonic-file");
  }
  return mnemonic.trim();
}

function parseArgs(argv: string[]): CliArgs {
  const args: CliArgs = {
    caseName: [],
    network: "Testnet",
    path: DEFAULT_PATH,
    trezorctl: "trezorctl",
    transport: "auto",
    hardwareSign: false,
    chunkify: false,
    outDir: DEFAULT_OUT_DIR,
    outCaseFile: DEFAULT_CASE_FILE,
    outRecipeFile: DEFAULT_FIXTURE_RECIPE_FILE,
    send: false,
    generateFixtureRecipes: false,
    fixtureName: [],
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--recipe-file") {
      args.recipeFile = argv[++i];
    } else if (arg === "--case-name") {
      args.caseName.push(argv[++i]);
    } else if (arg === "--mnemonic-file") {
      args.mnemonicFile = argv[++i];
    } else if (arg === "--network") {
      const network = argv[++i];
      if (!isNetwork(network)) {
        throw new Error(`unsupported --network: ${network}`);
      }
      args.network = network;
    } else if (arg === "--path") {
      args.path = argv[++i];
    } else if (arg === "--external-path") {
      args.externalPath = argv[++i];
    } else if (arg === "--transport") {
      args.transport = argv[++i];
    } else if (arg === "--trezorctl") {
      args.trezorctl = argv[++i];
    } else if (arg === "--out-dir") {
      args.outDir = argv[++i];
    } else if (arg === "--out-case-file") {
      args.outCaseFile = argv[++i];
    } else if (arg === "--out-recipe-file") {
      args.outRecipeFile = argv[++i];
    } else if (arg === "--generate-fixture-recipes") {
      args.generateFixtureRecipes = true;
    } else if (arg === "--fixture-name") {
      args.fixtureName.push(argv[++i]);
    } else if (arg === "--from-address") {
      args.fromAddress = argv[++i];
    } else if (arg === "--to-address") {
      args.toAddress = argv[++i];
    } else if (arg === "--hardware-sign") {
      args.hardwareSign = true;
    } else if (arg === "--chunkify") {
      args.chunkify = true;
    } else if (arg === "--send") {
      args.send = true;
    } else if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return args;
}

function printHelp(): void {
  console.log(`Usage:
  tsx src/ckb_tx_factory.ts --recipe-file recipes.testnet.json [--send]
  tsx src/ckb_tx_factory.ts --generate-fixture-recipes --from-address ckt1...

Options:
  --recipe-file FILE      JSON recipe file.
  --case-name NAME        Run only the named recipe. Can be repeated.
  --mnemonic-file FILE    Read mnemonic from file. Otherwise uses CKB_TEST_MNEMONIC.
  --network NAME          Network for generated fixture recipes. Default: Testnet.
  --path PATH             Derivation path. Default: ${DEFAULT_PATH}
  --external-path PATH    Derive external recipient from mnemonic, or from Trezor with --hardware-sign.
  --transport TRANSPORT   Trezor transport stored in generated case defaults. Default: auto.
  --trezorctl PATH        trezorctl executable for --hardware-sign. Default: trezorctl.
  --out-dir DIR           Output artifacts directory. Default: ${DEFAULT_OUT_DIR}
  --out-case-file FILE    Generated ckb-pytest case file. Default: ${DEFAULT_CASE_FILE}
  --generate-fixture-recipes
                         Generate recipe JSON whose names match pytest fixture_name values.
  --fixture-name NAME     Generate only the named pytest fixture recipe. Can be repeated.
  --from-address ADDRESS  Sender address for generated fixture recipes. Derived from mnemonic when omitted.
  --to-address ADDRESS    External recipient for generated fixture recipes. Defaults to --external-path or --from-address.
  --out-recipe-file FILE  Generated recipe file. Default: ${DEFAULT_FIXTURE_RECIPE_FILE}
  --hardware-sign         Use trezorctl ckb sign-tx instead of mnemonic signing. Requires --from-address.
  --chunkify              Pass --chunkify to trezorctl sign-tx.
  --send                  Broadcast transactions and generate compare cases.
  -h, --help              Show this help.
`);
}

async function main(argv = process.argv.slice(2)): Promise<number> {
  const args = parseArgs(argv);
  if (args.help) {
    printHelp();
    return 0;
  }
  if (args.generateFixtureRecipes) {
    let fromAddress = args.fromAddress;
    let toAddress = args.toAddress;
    let mnemonic: string | undefined;
    if (args.hardwareSign) {
      if (!fromAddress) {
        fromAddress = runTrezorctlGetAddress(
          buildTrezorctlGetAddressCommand({
            trezorctl: args.trezorctl,
            transport: args.transport,
            network: args.network,
            path: args.path,
          }),
        );
        console.log(`derived hardware from address: ${fromAddress}`);
      }
      if (!toAddress && args.externalPath) {
        toAddress = runTrezorctlGetAddress(
          buildTrezorctlGetAddressCommand({
            trezorctl: args.trezorctl,
            transport: args.transport,
            network: args.network,
            path: args.externalPath,
          }),
        );
        console.log(`derived hardware external address: ${toAddress}`);
      }
    } else {
      mnemonic =
        args.fromAddress && !args.externalPath && !args.send ? undefined : readMnemonic(args);
    }
    const payload = await buildFixtureRecipePayloadFromOptions({
      mnemonic,
      fromAddress,
      externalAddress: toAddress,
      externalPath: args.hardwareSign ? undefined : args.externalPath,
      fixtureNames: args.fixtureName,
      network: args.network,
      path: args.path,
      transport: args.transport,
    });
    ensureParentDir(args.outRecipeFile);
    fs.writeFileSync(args.outRecipeFile, `${JSON.stringify(payload, null, 2)}\n`);
    console.log(`wrote fixture recipe file: ${args.outRecipeFile}`);
    if (!args.send) {
      return 0;
    }

    const recipes = loadRecipesFromObject(payload);
    fs.mkdirSync(args.outDir, { recursive: true });
    const submitted: SubmittedTx[] = [];
    for (const recipe of recipes) {
      console.log(`[${recipe.name}] building transaction`);
      const result = args.hardwareSign
        ? await prepareAndMaybeSubmitRecipeWithHardware({
            recipe,
            send: true,
            outDir: args.outDir,
            trezorctl: args.trezorctl,
            chunkify: args.chunkify,
          })
        : await prepareAndMaybeSubmitRecipe({
            recipe,
            mnemonic: mnemonic ?? readMnemonic(args),
            send: true,
            outDir: args.outDir,
          });
      console.log(`[${recipe.name}] sent: ${result.txHash}`);
      if (result.txHash) {
        submitted.push({ name: recipe.name, txHash: result.txHash });
      }
    }
    if (submitted.length > 0) {
      const caseFile = buildCompareCases(recipes, submitted);
      ensureParentDir(args.outCaseFile);
      fs.writeFileSync(args.outCaseFile, `${JSON.stringify(caseFile, null, 2)}\n`);
      console.log(`wrote compare case file: ${args.outCaseFile}`);
    }
    return 0;
  }
  if (!args.recipeFile) {
    throw new Error("--recipe-file is required");
  }

  const selected = new Set(args.caseName);
  let recipes = loadRecipesFromFile(args.recipeFile);
  if (selected.size > 0) {
    recipes = recipes.filter((recipe) => selected.has(recipe.name));
    if (recipes.length === 0) {
      throw new Error("no recipe matched --case-name");
    }
  }

  const mnemonic = args.hardwareSign ? undefined : readMnemonic(args);
  fs.mkdirSync(args.outDir, { recursive: true });

  const submitted: SubmittedTx[] = [];
  for (const recipe of recipes) {
    console.log(`[${recipe.name}] building transaction`);
    const result = args.hardwareSign
      ? await prepareAndMaybeSubmitRecipeWithHardware({
          recipe,
          send: args.send,
          outDir: args.outDir,
          trezorctl: args.trezorctl,
          chunkify: args.chunkify,
        })
      : await prepareAndMaybeSubmitRecipe({
          recipe,
          mnemonic: mnemonic as string,
          send: args.send,
          outDir: args.outDir,
        });
    console.log(
      `[${recipe.name}] ${result.status}${result.txHash ? `: ${result.txHash}` : ""}`,
    );
    if (result.txHash) {
      submitted.push({ name: recipe.name, txHash: result.txHash });
    }
  }

  if (submitted.length > 0) {
    const caseFile = buildCompareCases(recipes, submitted);
    ensureParentDir(args.outCaseFile);
    fs.writeFileSync(args.outCaseFile, `${JSON.stringify(caseFile, null, 2)}\n`);
    console.log(`wrote compare case file: ${args.outCaseFile}`);
  }

  return 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().then(
    (code) => {
      process.exit(code);
    },
    (error: unknown) => {
      console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
      process.exit(1);
    },
  );
}
