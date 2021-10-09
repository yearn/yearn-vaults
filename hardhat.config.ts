import "@typechain/hardhat";
import "@nomiclabs/hardhat-ethers";

import { HardhatUserConfig } from "hardhat/types";

const config: HardhatUserConfig = {
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
    typechain: {
        outDir: "typechain",
        target: "ethers-v5",
    },
};
export default config;
