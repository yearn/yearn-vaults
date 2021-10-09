import "@typechain/hardhat";
import "@nomiclabs/hardhat-ethers";
import { config as dotenvConfig } from "dotenv";
dotenvConfig({ path: resolve(__dirname, "./.env") });

import { HardhatUserConfig } from "hardhat/types";

const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || "";
const INFURA_API_KEY = process.env.INFURA_API_KEY || "";
const ALCHEMY_KEY = process.env.ALCHEMY_KEY || "";

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
