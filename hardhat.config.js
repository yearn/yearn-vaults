/**
* Hardhat Configuration
* @module hardhat
*/
module.exports = {
solidity: {
    version: "0.6.12",
    settings: {
        metadata: {
            bytecodeHash: "none",
        },
        optimizer: {
            enabled: false,
            runs: 200,
            details: {
                yul: false,
            },
        },
    },
  },
}
