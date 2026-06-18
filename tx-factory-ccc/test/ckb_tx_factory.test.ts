import assert from "node:assert/strict";
import test from "node:test";

import {
  applyTrezorSignatureToTransaction,
  buildCompareCases,
  buildFixtureRecipePayloadFromOptions,
  deriveAddressFromMnemonic,
  derivePrivateKeyFromMnemonic,
  estimateCyclesBeforeSend,
  loadRecipesFromObject,
  parseTrezorctlGetAddressOutput,
  parseTrezorctlSignTxOutput,
  shannonsFromCkb,
} from "../src/ckb_tx_factory.ts";
import * as ccc from "@ckb-ccc/core";
import {
  SUPPORTED_ONCHAIN_FIXTURE_NAMES,
  buildOnchainFixtureRecipePayload,
} from "../src/fixture_recipes.ts";

test("derives CKB private key from mnemonic and path", () => {
  const mnemonic = "all all all all all all all all all all all all";

  assert.equal(
    derivePrivateKeyFromMnemonic(mnemonic, "m/44'/309'/0'/0/0"),
    "0xddcb341aea9acc36a3101a22ef8d28e1ed2680ed4a740a92d070dc0bb410f8bb",
  );
});

test("derives Testnet address from mnemonic and path", async () => {
  const mnemonic = "all all all all all all all all all all all all";

  assert.equal(
    await deriveAddressFromMnemonic(mnemonic, { network: "Testnet" }),
    "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqg2l882x57v5q8tzu78ggz50c6c46k39rcrudmgs",
  );
});

test("builds selected fixture recipe payload from mnemonic-derived address", async () => {
  const payload = await buildFixtureRecipePayloadFromOptions({
    mnemonic: "all all all all all all all all all all all all",
    network: "Testnet",
    fixtureNames: ["one-input-default-witness"],
  });

  assert.equal(
    payload.defaults.from_address,
    "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqg2l882x57v5q8tzu78ggz50c6c46k39rcrudmgs",
  );
  assert.deepEqual(
    payload.recipes.map((recipe) => recipe.name),
    ["one-input-default-witness"],
  );
});

test("derives external fixture address from a different mnemonic path", async () => {
  const mnemonic = "all all all all all all all all all all all all";
  const payload = await buildFixtureRecipePayloadFromOptions({
    mnemonic,
    network: "Testnet",
    fixtureNames: ["external-output-plus-change"],
    externalPath: "m/44'/309'/0'/0/1",
  });

  assert.equal(
    payload.defaults.from_address,
    "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqg2l882x57v5q8tzu78ggz50c6c46k39rcrudmgs",
  );
  assert.notEqual(payload.defaults.to_address, payload.defaults.from_address);
  assert.equal(payload.recipes[0]?.to_address, payload.defaults.to_address);
});

test("loads recipes with defaults and keeps per-recipe overrides", () => {
  const payload = {
    defaults: {
      network: "Testnet",
      from_address: "ckt1from",
      path: "m/44'/309'/0'/0/0",
      transport: "webusb:000:1",
      signature_policy: "require",
      fee_rate: 1000,
    },
    recipes: [
      {
        name: "self",
        kind: "self_transfer",
      },
      {
        name: "send-100",
        kind: "transfer",
        to_address: "ckt1to",
        amount_ckb: "100",
        signature_policy: "compare",
      },
    ],
  };

  const recipes = loadRecipesFromObject(payload);

  assert.equal(recipes.length, 2);
  assert.equal(recipes[0]?.name, "self");
  assert.equal(recipes[0]?.fromAddress, "ckt1from");
  assert.equal(recipes[0]?.feeRate, 1000);
  assert.equal(recipes[1]?.signaturePolicy, "compare");
  assert.equal(recipes[1]?.amountShannons, 10_000_000_000n);
});

test("rejects duplicate recipe names", () => {
  assert.throws(
    () =>
      loadRecipesFromObject({
        defaults: {
          from_address: "ckt1from",
        },
        recipes: [
          { name: "dup", kind: "self_transfer" },
          { name: "dup", kind: "self_transfer" },
        ],
      }),
    /duplicate recipe name/,
  );
});

test("converts decimal CKB to shannons exactly", () => {
  assert.equal(shannonsFromCkb("1"), 100_000_000n);
  assert.equal(shannonsFromCkb("0.001"), 100_000n);
  assert.equal(shannonsFromCkb("100.12345678"), 10_012_345_678n);
  assert.throws(() => shannonsFromCkb("0.000000001"), /up to 8 decimals/);
});

test("builds ckb-pytest case json from submitted txs", () => {
  const recipes = loadRecipesFromObject({
    defaults: {
      network: "Testnet",
      from_address: "ckt1from",
      path: "m/44'/309'/0'/0/0",
      transport: "webusb:000:1",
      signature_policy: "require",
    },
    recipes: [{ name: "self", kind: "self_transfer" }],
  });
  const cases = buildCompareCases(recipes, [
    { name: "self", txHash: `0x${"11".repeat(32)}` },
  ]);

  assert.deepEqual(cases, {
    defaults: {
      network: "Testnet",
      address: "ckt1from",
      path: "m/44'/309'/0'/0/0",
      transport: "webusb:000:1",
      signature_policy: "require",
    },
    cases: [{ name: "self", tx_hash: `0x${"11".repeat(32)}` }],
  });
});

test("builds compare case json for both groups of a mixed lock transaction", () => {
  const recipes = loadRecipesFromObject({
    defaults: {
      network: "Testnet",
      from_address: "ckt1primary",
      path: "m/44'/309'/0'/0/0",
      transport: "webusb:000:1",
      signature_policy: "compare",
    },
    recipes: [
      {
        name: "mixed-lock-groups-input-output-type",
        kind: "mixed_lock_groups",
        secondary_address: "ckt1secondary",
        secondary_path: "m/44'/309'/0'/0/1",
      },
    ],
  });
  const cases = buildCompareCases(recipes, [
    {
      name: "mixed-lock-groups-input-output-type",
      txHash: `0x${"44".repeat(32)}`,
    },
  ]);

  assert.deepEqual(cases, {
    defaults: {
      network: "Testnet",
      address: "ckt1primary",
      path: "m/44'/309'/0'/0/0",
      transport: "webusb:000:1",
      signature_policy: "compare",
    },
    cases: [
      {
        name: "mixed-lock-groups-input-output-type-primary",
        tx_hash: `0x${"44".repeat(32)}`,
      },
      {
        name: "mixed-lock-groups-input-output-type-secondary",
        address: "ckt1secondary",
        path: "m/44'/309'/0'/0/1",
        tx_hash: `0x${"44".repeat(32)}`,
      },
    ],
  });
});

test("builds fixture recipe payload with names matching onchain_compare fixture names", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    externalAddress: "ckt1external",
  });

  assert.deepEqual(
    payload.recipes.map((recipe) => recipe.name),
    [...SUPPORTED_ONCHAIN_FIXTURE_NAMES],
  );
  assert.equal(payload.defaults?.from_address, "ckt1from");
  assert.equal(payload.defaults?.to_address, "ckt1external");

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.name, "self-send-change-only");
  assert.equal(recipes[1]?.name, "external-output-plus-change");
  assert.equal(recipes[1]?.toAddress, "ckt1external");
});

test("builds fixture recipe payload for selected fixture names only", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    externalAddress: "ckt1external",
    externalPath: "m/44'/309'/0'/0/1",
    fixtureNames: ["self-send-change-only"],
  });

  assert.deepEqual(
    payload.recipes.map((recipe) => recipe.name),
    ["self-send-change-only"],
  );
  assert.equal(payload.recipes[0]?.kind, "self_transfer");
});

test("builds two input same lock fixture as deterministic two-stage recipe", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    fixtureNames: ["two-inputs-same-lock-group"],
  });

  assert.deepEqual(payload.recipes, [
    {
      name: "two-inputs-same-lock-group",
      kind: "two_stage_same_lock",
      funding_amount_ckb: "62",
      amount_ckb: "123",
    },
  ]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "two_stage_same_lock");
  assert.equal(recipes[0]?.fundingAmountShannons, 6_200_000_000n);
  assert.equal(recipes[0]?.amountShannons, 12_300_000_000n);
});

test("builds 50 inputs 1 output boundary fixture as single-output recipe", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    fixtureNames: ["50-inputs-1-output"],
  });

  assert.deepEqual(payload.recipes, [
    {
      name: "50-inputs-1-output",
      kind: "two_stage_many_inputs_one_output",
      funding_amount_ckb: "62",
      funding_output_count: 50,
    },
  ]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "two_stage_many_inputs_one_output");
  assert.equal(recipes[0]?.fundingAmountShannons, 6_200_000_000n);
  assert.equal(recipes[0]?.amountShannons, 6_200_000_000n);
  assert.equal(recipes[0]?.fundingOutputCount, 50);
  assert.equal(recipes[0]?.targetInputCount, 50);
});

test("builds witness payload fixtures as deterministic two-stage recipes", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    fixtureNames: [
      "trailing-witness",
      "first-group-input-type",
      "first-group-output-type",
      "same-lock-group-non-empty-witness",
      "first-group-input-output-type",
      "witness-args-and-random-raw",
    ],
  });

  assert.deepEqual(
    payload.recipes.map((recipe) => recipe.name),
    [
      "trailing-witness",
      "first-group-input-type",
      "first-group-output-type",
      "same-lock-group-non-empty-witness",
      "first-group-input-output-type",
      "witness-args-and-random-raw",
    ],
  );
  assert.deepEqual(
    payload.recipes.map((recipe) => recipe.kind),
    [
      "two_stage_witness_payload",
      "two_stage_witness_payload",
      "two_stage_witness_payload",
      "two_stage_witness_payload",
      "two_stage_witness_payload",
      "two_stage_witness_payload",
    ],
  );

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.trailingWitness, "0x010203");
  assert.equal(recipes[1]?.witnessInputType, "0x0102");
  assert.equal(recipes[2]?.witnessOutputType, "0x0304");
  assert.equal(recipes[3]?.targetInputCount, 2);
  assert.equal(recipes[3]?.sameGroupSecondWitness, "0x050607");
  assert.equal(recipes[4]?.witnessInputType, "0x0102");
  assert.equal(recipes[4]?.witnessOutputType, "0x0304");
  assert.equal(recipes[5]?.targetInputCount, 2);
  assert.equal(recipes[5]?.witnessInputType, "0x0102");
  assert.equal(recipes[5]?.witnessOutputType, "0x0304");
  assert.equal(recipes[5]?.sameGroupSecondWitness, "0xa1b2c3d4e5");
  assert.equal(recipes[5]?.trailingWitness, "0x0badc0ffee");
});

test("builds mixed lock group fixture with secondary path and compare policy", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    externalAddress: "ckt1secondary",
    externalPath: "m/44'/309'/0'/0/1",
    fixtureNames: ["mixed-lock-groups"],
  });

  assert.deepEqual(payload.recipes, [
    {
      name: "mixed-lock-groups",
      kind: "mixed_lock_groups",
      amount_ckb: "130",
      secondary_address: "ckt1secondary",
      secondary_path: "m/44'/309'/0'/0/1",
      secondary_amount_ckb: "124",
      primary_input_count: 2,
      secondary_input_count: 2,
      signature_policy: "compare",
    },
  ]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "mixed_lock_groups");
  assert.equal(recipes[0]?.secondaryAddress, "ckt1secondary");
  assert.equal(recipes[0]?.secondaryPath, "m/44'/309'/0'/0/1");
  assert.equal(recipes[0]?.primaryInputCount, 2);
  assert.equal(recipes[0]?.secondaryInputCount, 2);
  assert.equal(recipes[0]?.signaturePolicy, "compare");
});

test("builds mixed lock group witness payload fixture for both account groups", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    externalAddress: "ckt1secondary",
    externalPath: "m/44'/309'/0'/0/1",
    fixtureNames: ["mixed-lock-groups-input-output-type"],
  });

  assert.deepEqual(payload.recipes, [
    {
      name: "mixed-lock-groups-input-output-type",
      kind: "mixed_lock_groups",
      amount_ckb: "130",
      secondary_address: "ckt1secondary",
      secondary_path: "m/44'/309'/0'/0/1",
      secondary_amount_ckb: "124",
      primary_input_count: 2,
      secondary_input_count: 2,
      primary_witness_input_type: "0x0102",
      primary_witness_output_type: "0x0304",
      secondary_witness_input_type: "0x0506",
      secondary_witness_output_type: "0x0708",
      signature_policy: "compare",
    },
  ]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "mixed_lock_groups");
  assert.equal(recipes[0]?.primaryWitnessInputType, "0x0102");
  assert.equal(recipes[0]?.primaryWitnessOutputType, "0x0304");
  assert.equal(recipes[0]?.secondaryWitnessInputType, "0x0506");
  assert.equal(recipes[0]?.secondaryWitnessOutputType, "0x0708");
  assert.equal(recipes[0]?.signaturePolicy, "compare");
});

test("builds xUDT mint and transfer fixture recipes", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    externalAddress: "ckt1recipient",
    fixtureNames: ["xudt-mint", "xudt-transfer"],
  });

  assert.deepEqual(payload.recipes, [
    {
      name: "xudt-mint",
      kind: "xudt_mint",
      xudt_amount: "1000000",
      xudt_cell_capacity_ckb: "150",
    },
    {
      name: "xudt-transfer",
      kind: "xudt_transfer",
      to_address: "ckt1recipient",
      xudt_amount: "400000",
      xudt_change_amount: "600000",
      xudt_cell_capacity_ckb: "150",
    },
  ]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "xudt_mint");
  assert.equal(recipes[0]?.xudtAmount, 1_000_000n);
  assert.equal(recipes[0]?.xudtCellCapacityShannons, 15_000_000_000n);
  assert.equal(recipes[1]?.kind, "xudt_transfer");
  assert.equal(recipes[1]?.toAddress, "ckt1recipient");
  assert.equal(recipes[1]?.xudtAmount, 400_000n);
  assert.equal(recipes[1]?.xudtChangeAmount, 600_000n);
});

test("builds DAO deposit and withdraw1 fixture recipes", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    fixtureNames: ["dao-deposit", "dao-withdraw1"],
  });

  assert.deepEqual(payload.recipes, [
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
  ]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "dao_deposit");
  assert.equal(recipes[0]?.amountShannons, 10_200_000_000n);
  assert.equal(recipes[1]?.kind, "dao_withdraw1");
  assert.equal(recipes[1]?.amountShannons, 10_200_000_000n);
});

test("builds supplemental type, cell_dep, and hash_type fixture recipes", () => {
  const payload = buildOnchainFixtureRecipePayload({
    fromAddress: "ckt1from",
    externalAddress: "ckt1recipient",
    fixtureNames: [
      "output-with-type-script",
      "multiple-cell-deps-ordered",
      "long-lock-args-chunkify",
      "long-type-args",
      "lock-hash-type-data1",
      "lock-hash-type-data2",
      "type-hash-type-data1-data2",
    ],
  });

  assert.deepEqual(
    payload.recipes.map((recipe) => recipe.name),
    [
      "output-with-type-script",
      "multiple-cell-deps-ordered",
      "long-lock-args-chunkify",
      "long-type-args",
      "lock-hash-type-data1",
      "lock-hash-type-data2",
      "type-hash-type-data1-data2",
    ],
  );

  assert.deepEqual(payload.recipes[0], {
    name: "output-with-type-script",
    kind: "custom_type_outputs",
    amount_ckb: "150",
    custom_type_hash_types: ["data1"],
    custom_type_args: "0x",
  });
  assert.deepEqual(payload.recipes[1], {
    name: "multiple-cell-deps-ordered",
    kind: "transfer",
    to_address: "ckt1recipient",
    amount_ckb: "62",
    extra_known_cell_deps: ["XUdt", "AlwaysSuccess"],
  });
  assert.equal(payload.recipes[2]?.kind, "custom_lock_output");
  assert.equal(payload.recipes[2]?.amount_ckb, "200");
  assert.equal(payload.recipes[2]?.custom_lock_hash_type, "type");
  assert.equal(payload.recipes[2]?.custom_lock_args?.length, 2 + 128 * 2);
  assert.equal(payload.recipes[3]?.kind, "custom_type_outputs");
  assert.equal(payload.recipes[3]?.amount_ckb, "300");
  assert.equal(payload.recipes[3]?.custom_type_args?.length, 2 + 128 * 2);
  assert.equal(payload.recipes[4]?.custom_lock_hash_type, "data1");
  assert.equal(payload.recipes[5]?.custom_lock_hash_type, "data2");
  assert.deepEqual(payload.recipes[6]?.custom_type_hash_types, ["data1", "data2"]);

  const recipes = loadRecipesFromObject(payload);
  assert.equal(recipes[0]?.kind, "custom_type_outputs");
  assert.deepEqual(recipes[0]?.customTypeHashTypes, ["data1"]);
  assert.deepEqual(recipes[1]?.extraKnownCellDeps, ["XUdt", "AlwaysSuccess"]);
  assert.equal(recipes[2]?.customLockHashType, "type");
  assert.equal(recipes[2]?.customLockArgs?.length, 2 + 128 * 2);
  assert.equal(recipes[3]?.customTypeArgs?.length, 2 + 128 * 2);
  assert.equal(recipes[4]?.customLockHashType, "data1");
  assert.equal(recipes[5]?.customLockHashType, "data2");
  assert.deepEqual(recipes[6]?.customTypeHashTypes, ["data1", "data2"]);
});

test("normalizes output_data for fixture recipes that exercise outputs_data hashing", () => {
  const recipes = loadRecipesFromObject({
    defaults: {
      from_address: "ckt1from",
    },
    recipes: [
      {
        name: "output-data-present",
        kind: "transfer",
        to_address: "ckt1from",
        amount_ckb: "62",
        output_data: "0x01020304",
      },
      {
        name: "multi-output-with-data",
        kind: "multi_output",
        outputs: [
          { to_address: "ckt1from", amount_ckb: "62", data: "0xabcd" },
          { to_address: "ckt1from", amount_ckb: "63" },
        ],
      },
    ],
  });

  assert.equal(recipes[0]?.outputData, "0x01020304");
  assert.equal(recipes[1]?.outputs?.[0]?.data, "0xabcd");
  assert.equal(recipes[1]?.outputs?.[1]?.data, "0x");
});

test("parses trezorctl ckb sign-tx output", () => {
  const signature = `0x${"11".repeat(65)}`;
  const txHash = `0x${"22".repeat(32)}`;

  assert.deepEqual(
    parseTrezorctlSignTxOutput(`Signature: ${signature}\nTX Hash: ${txHash}\n`),
    {
      signature,
      txHash,
    },
  );
});

test("parses trezorctl ckb get-address output", () => {
  assert.equal(
    parseTrezorctlGetAddressOutput(
      "Please confirm action on your Trezor device.\nckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed\n",
    ),
    "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
  );
});

test("rejects trezorctl get-address output without a CKB address", () => {
  assert.throws(
    () => parseTrezorctlGetAddressOutput("Error: No Trezor device found"),
    /did not contain a CKB address/,
  );
});

test("applies trezor signature to witness lock", () => {
  const tx = ccc.Transaction.default();
  tx.setWitnessArgsAt(
    0,
    ccc.WitnessArgs.from({
      lock: `0x${"00".repeat(65)}`,
    }),
  );
  const signature = `0x${"33".repeat(65)}` as `0x${string}`;

  applyTrezorSignatureToTransaction(tx, signature, 0);

  assert.equal(tx.getWitnessArgsAt(0)?.lock, signature);
});

test("estimate_cycles preflight returns cycles before send", async () => {
  const tx = ccc.Transaction.default();
  const client = {
    estimateCycles: async () => 12345n,
  } as unknown as ccc.Client;

  assert.deepEqual(await estimateCyclesBeforeSend(client, tx), {
    status: "ok",
    cycles: "12345",
  });
});

test("estimate_cycles preflight rejects before send when RPC rejects", async () => {
  const tx = ccc.Transaction.default();
  const client = {
    estimateCycles: async () => {
      throw new Error("ValidationFailure");
    },
  } as unknown as ccc.Client;

  await assert.rejects(
    () => estimateCyclesBeforeSend(client, tx),
    /estimate_cycles failed: ValidationFailure/,
  );
});
