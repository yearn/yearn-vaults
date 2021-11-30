
// See https://hardhat.org/config/ for config options.
module.exports = {
  networks: {
    hardhat: {
      hardfork: "london",
      // base fee of 0 allows use of 0 gas price when testing
      initialBaseFeePerGas: 0,
      accounts: {
        mnemonic: "test test test test test test test test test test test junk",
        path: "m/44'/60'/0'",
        count: 10,
      }
    },
  },
};
