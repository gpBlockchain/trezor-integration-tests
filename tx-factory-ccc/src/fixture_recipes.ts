import type { Network, RawOutput, RawRecipe, RecipePayload, SignaturePolicy } from "./ckb_tx_factory.ts";

const DEFAULT_FIXTURE_PATH = "m/44'/309'/0'/0/0";
const DEFAULT_FIXTURE_FEE_RATE = 1000;

export const SUPPORTED_ONCHAIN_FIXTURE_NAMES = [
  "self-send-change-only",
  "external-output-plus-change",
  "multiple-inputs-same-account",
  "output-data-present",
  "one-input-default-witness",
  "two-inputs-same-lock-group",
  "trailing-witness",
  "first-group-input-type",
  "first-group-output-type",
  "same-lock-group-non-empty-witness",
  "first-group-input-output-type",
  "witness-args-and-random-raw",
  "50-inputs-1-output",
  "1-input-50-outputs",
  "50-inputs-50-outputs",
  "100kb-output-data",
  "100-inputs-100-outputs",
  "mixed-lock-groups",
  "mixed-lock-groups-input-output-type",
  "output-with-type-script",
  "multiple-cell-deps-ordered",
  "long-lock-args-chunkify",
  "long-type-args",
  "lock-hash-type-data1",
  "lock-hash-type-data2",
  "type-hash-type-data1-data2",
  "xudt-mint",
  "xudt-transfer",
  "dao-deposit",
  "dao-withdraw1",
] as const;

export type SupportedOnchainFixtureName = (typeof SUPPORTED_ONCHAIN_FIXTURE_NAMES)[number];

export type FixtureRecipePayload = RecipePayload & {
  defaults: RawRecipe;
  recipes: RawRecipe[];
};

export type FixtureRecipeOptions = {
  fromAddress: string;
  externalAddress?: string;
  fixtureNames?: string[];
  network?: Network;
  path?: string;
  externalPath?: string;
  transport?: string;
  signaturePolicy?: SignaturePolicy;
  feeRate?: number;
  waitCommitted?: boolean;
};

function repeatedOutputs(toAddress: string, count: number, amountCkb: string): RawOutput[] {
  return Array.from({ length: count }, () => ({
    to_address: toAddress,
    amount_ckb: amountCkb,
  }));
}

function outputData(byteLength: number, byteHex = "00"): string {
  if (!/^[0-9a-fA-F]{2}$/.test(byteHex)) {
    throw new Error("byteHex must be exactly one hex byte");
  }
  return `0x${byteHex.repeat(byteLength)}`;
}

function hexBytes(byteLength: number, byteHex: string): string {
  return outputData(byteLength, byteHex);
}

export function buildOnchainFixtureRecipePayload(
  options: FixtureRecipeOptions,
): FixtureRecipePayload {
  const externalAddress = options.externalAddress ?? options.fromAddress;
  const defaults: RawRecipe = {
    network: options.network ?? "Testnet",
    from_address: options.fromAddress,
    to_address: externalAddress,
    path: options.path ?? DEFAULT_FIXTURE_PATH,
    transport: options.transport ?? "auto",
    signature_policy: options.signaturePolicy ?? "require",
    fee_rate: options.feeRate ?? DEFAULT_FIXTURE_FEE_RATE,
    wait_committed: options.waitCommitted ?? true,
  };

  const allRecipes: RawRecipe[] = [
    {
      name: "self-send-change-only",
      kind: "self_transfer",
      amount_ckb: "62",
    },
    {
      name: "external-output-plus-change",
      kind: "transfer",
      to_address: externalAddress,
      amount_ckb: "62",
    },
    {
      name: "multiple-inputs-same-account",
      kind: "self_transfer",
      amount_ckb: "130",
    },
    {
      name: "output-data-present",
      kind: "transfer",
      to_address: externalAddress,
      amount_ckb: "65",
      output_data: "0x01020304",
    },
    {
      name: "one-input-default-witness",
      kind: "self_transfer",
      amount_ckb: "62",
    },
    {
      name: "two-inputs-same-lock-group",
      kind: "two_stage_same_lock",
      funding_amount_ckb: "62",
      amount_ckb: "123",
    },
    {
      name: "trailing-witness",
      kind: "two_stage_witness_payload",
      funding_amount_ckb: "62",
      amount_ckb: "62",
      trailing_witness: "0x010203",
    },
    {
      name: "first-group-input-type",
      kind: "two_stage_witness_payload",
      funding_amount_ckb: "62",
      amount_ckb: "62",
      witness_input_type: "0x0102",
    },
    {
      name: "first-group-output-type",
      kind: "two_stage_witness_payload",
      funding_amount_ckb: "62",
      amount_ckb: "62",
      witness_output_type: "0x0304",
    },
    {
      name: "same-lock-group-non-empty-witness",
      kind: "two_stage_witness_payload",
      funding_amount_ckb: "62",
      amount_ckb: "123",
      target_input_count: 2,
      same_group_second_witness: "0x050607",
    },
    {
      name: "first-group-input-output-type",
      kind: "two_stage_witness_payload",
      funding_amount_ckb: "62",
      amount_ckb: "62",
      witness_input_type: "0x0102",
      witness_output_type: "0x0304",
    },
    {
      name: "witness-args-and-random-raw",
      kind: "two_stage_witness_payload",
      funding_amount_ckb: "62",
      amount_ckb: "123",
      target_input_count: 2,
      witness_input_type: "0x0102",
      witness_output_type: "0x0304",
      same_group_second_witness: "0xa1b2c3d4e5",
      trailing_witness: "0x0badc0ffee",
    },
    {
      name: "50-inputs-1-output",
      kind: "two_stage_many_inputs_one_output",
      funding_amount_ckb: "62",
      funding_output_count: 50,
    },
    {
      name: "1-input-50-outputs",
      kind: "multi_output",
      outputs: repeatedOutputs(externalAddress, 50, "62"),
    },
    {
      name: "50-inputs-50-outputs",
      kind: "multi_output",
      outputs: repeatedOutputs(externalAddress, 50, "62"),
    },
    {
      name: "100kb-output-data",
      kind: "transfer",
      to_address: externalAddress,
      amount_ckb: "102465",
      output_data: outputData(100 * 1024),
    },
    {
      name: "100-inputs-100-outputs",
      kind: "multi_output",
      outputs: repeatedOutputs(externalAddress, 100, "62"),
    },
    {
      name: "mixed-lock-groups",
      kind: "mixed_lock_groups",
      amount_ckb: "130",
      secondary_address: externalAddress,
      secondary_path: options.externalPath,
      secondary_amount_ckb: "124",
      primary_input_count: 2,
      secondary_input_count: 2,
    },
    {
      name: "mixed-lock-groups-input-output-type",
      kind: "mixed_lock_groups",
      amount_ckb: "130",
      secondary_address: externalAddress,
      secondary_path: options.externalPath,
      secondary_amount_ckb: "124",
      primary_input_count: 2,
      secondary_input_count: 2,
      primary_witness_input_type: "0x0102",
      primary_witness_output_type: "0x0304",
      secondary_witness_input_type: "0x0506",
      secondary_witness_output_type: "0x0708",
    },
    {
      name: "output-with-type-script",
      kind: "custom_type_outputs",
      amount_ckb: "150",
      custom_type_hash_types: ["data1"],
      custom_type_args: "0x",
    },
    {
      name: "multiple-cell-deps-ordered",
      kind: "transfer",
      to_address: externalAddress,
      amount_ckb: "62",
      extra_known_cell_deps: ["XUdt", "AlwaysSuccess"],
    },
    {
      name: "long-lock-args-chunkify",
      kind: "custom_lock_output",
      amount_ckb: "200",
      custom_lock_hash_type: "type",
      custom_lock_args: hexBytes(128, "11"),
    },
    {
      name: "long-type-args",
      kind: "custom_type_outputs",
      amount_ckb: "300",
      custom_type_hash_types: ["data1"],
      custom_type_args: hexBytes(128, "22"),
    },
    {
      name: "lock-hash-type-data1",
      kind: "custom_lock_output",
      amount_ckb: "62",
      custom_lock_hash_type: "data1",
      custom_lock_args: hexBytes(20, "33"),
    },
    {
      name: "lock-hash-type-data2",
      kind: "custom_lock_output",
      amount_ckb: "62",
      custom_lock_hash_type: "data2",
      custom_lock_args: hexBytes(20, "44"),
    },
    {
      name: "type-hash-type-data1-data2",
      kind: "custom_type_outputs",
      amount_ckb: "150",
      custom_type_hash_types: ["data1", "data2"],
      custom_type_args: "0x",
    },
    {
      name: "xudt-mint",
      kind: "xudt_mint",
      xudt_amount: "1000000",
      xudt_cell_capacity_ckb: "150",
    },
    {
      name: "xudt-transfer",
      kind: "xudt_transfer",
      to_address: externalAddress,
      xudt_amount: "400000",
      xudt_change_amount: "600000",
      xudt_cell_capacity_ckb: "150",
    },
    {
      name: "dao-deposit",
      kind: "dao_deposit",
      amount_ckb: "102",
    },
    {
      name: "dao-withdraw1",
      kind: "dao_withdraw1",
      amount_ckb: "102",
    },
  ];

  const selected = new Set(options.fixtureNames ?? []);
  if (selected.size === 0) {
    return { defaults, recipes: allRecipes };
  }

  const recipes = allRecipes.filter((recipe) => recipe.name && selected.has(recipe.name));
  if (recipes.length !== selected.size) {
    const available = new Set(allRecipes.map((recipe) => recipe.name));
    const missing = [...selected].filter((name) => !available.has(name));
    throw new Error(`unknown fixture name: ${missing.join(", ")}`);
  }
  return { defaults, recipes };
}
