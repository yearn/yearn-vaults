// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import {VaultAPI, BaseWrapper} from "./BaseWrapper.sol";

contract AffiliateToken is ERC20, BaseWrapper {
    address public affiliate;
    address public governance;
    address public pendingGovernance;

    /// @notice The EIP-712 typehash for the contract's domain
    bytes32 public constant DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,uint chainId,address verifyingContract)");
    bytes32 public immutable DOMAINSEPARATOR;

    /// @notice The EIP-712 typehash for the permit struct used by the contract
    bytes32 public constant PERMIT_TYPEHASH = keccak256("Permit(address owner,address spender,uint value,uint nonce,uint deadline)");

    /// @notice A record of states for signing / validating signatures
    mapping (address => uint) public nonces;

    function safe32(uint n, string memory errorMessage) internal pure returns (uint32) {
        require(n < 2**32, errorMessage);
        return uint32(n);
    }

    modifier onlyAffiliate() {
        require(msg.sender == affiliate);
        _;
    }

    function pricePerShare() external view returns (uint) {
        return bestVault().pricePerShare();
    }
    function apiVersion() external view returns (string memory) {
        return bestVault().apiVersion();
    }
    function maxAvailableShares() external view returns (uint) {
        return bestVault().maxAvailableShares();
    }
    function debtOutstanding() external view returns (uint) {
        return bestVault().debtOutstanding();
    }
    function debtOutstanding(address strategy) external view returns (uint) {
        return bestVault().debtOutstanding(strategy);
    }
    function creditAvailable() external view returns (uint) {
        return bestVault().creditAvailable();
    }
    function creditAvailable(address strategy) external view returns (uint) {
        return bestVault().creditAvailable(strategy);
    }
    function availableDepositLimit() external view returns (uint) {
        return bestVault().availableDepositLimit();
    }
    function expectedReturn() external view returns (uint) {
        return bestVault().expectedReturn();
    }
    function expectedReturn(address strategy) external view returns (uint) {
        return bestVault().expectedReturn(strategy);
    }
    function vname() external view returns (string memory) {
        return bestVault().name();
    }
    function vsymbol() external view returns (string memory) {
        return bestVault().symbol();
    }
    function vdecimals() external view returns (uint) {
        return bestVault().decimals();
    }
    function vbalanceOf(address owner) external view returns (uint) {
        return bestVault().balanceOf(owner);
    }
    function vtotalSupply() external view returns (uint) {
        return bestVault().totalSupply();
    }
    function vgovernance() external view returns (address) {
        return bestVault().governance();
    }
    function withdrawalQueue(uint position) external view returns (address) {
        return bestVault().withdrawalQueue(position);
    }
    function emergencyShutdown() external view returns (bool) {
        return bestVault().emergencyShutdown();
    }
    function depositLimit() external view returns (uint) {
        return bestVault().depositLimit();
    }
    function debtRatio() external view returns (uint) {
        return bestVault().debtRatio();
    }
    function totalDebt() external view returns (uint) {
        return bestVault().totalDebt();
    }
    function lastReport() external view returns (uint) {
        return bestVault().lastReport();
    }
    function activation() external view returns (uint) {
        return bestVault().activation();
    }
    function rewards() external view returns (address) {
        return bestVault().rewards();
    }
    function managementFee() external view returns (uint) {
        return bestVault().managementFee();
    }
    function performanceFee() external view returns (uint) {
        return bestVault().performanceFee();
    }

    function setGovernance(address _gov) external {
        require(msg.sender == governance);
        pendingGovernance = _gov;
    }

    function acceptGovernance() external {
        require(msg.sender == pendingGovernance);
        governance = pendingGovernance;
    }

    function setAffiliate(address _affiliate) external {
        require(msg.sender == governance || msg.sender == affiliate);
        affiliate = _affiliate;
    }

    constructor(
        address _token,
        string memory name,
        string memory symbol,
        address _affiliate,
        address _governance
    ) public BaseWrapper(_token) ERC20(name, symbol) {
        DOMAINSEPARATOR = keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(name)), _getChainId(), address(this)));
        affiliate = _affiliate;
        governance = _governance;
        _setupDecimals(uint8(token.decimals()));
    }

    function _shareValue(uint256 numShares) internal returns (uint256) {
        uint256 totalShares = totalSupply();

        if (totalShares > 0) {
            return totalBalance(address(this)).mul(numShares).div(totalShares);
        } else {
            return numShares;
        }
    }

    function _sharesForValue(uint256 amount) internal returns (uint256) {
        uint256 totalWrapperAssets = totalBalance(address(this));

        if (totalWrapperAssets > 0) {
            return totalSupply().mul(amount).div(totalWrapperAssets);
        } else {
            return amount;
        }
    }

    function deposit() external returns (uint256 deposited) {
        uint256 amount = IERC20(token).balanceOf(address(this));
        uint256 shares = _sharesForValue(amount); // NOTE: Must be calculated before deposit is handled
        deposited = _deposit(msg.sender, address(this), amount, true); // `true` = pull from `msg.sender`
        _mint(msg.sender, shares);
    }

    function deposit(uint256 amount) external returns (uint256 deposited) {
        uint256 shares = _sharesForValue(amount); // NOTE: Must be calculated before deposit is handled
        deposited = _deposit(msg.sender, address(this), amount, true); // `true` = pull from `msg.sender`
        _mint(msg.sender, shares);
    }

    /**
     * @notice Triggers an approval from owner to spends
     * @param owner The address to approve from
     * @param spender The address to be approved
     * @param amount The number of tokens that are approved (2^256-1 means infinite)
     * @param deadline The time at which to expire the signature
     * @param v The recovery byte of the signature
     * @param r Half of the ECDSA signature pair
     * @param s Half of the ECDSA signature pair
     */
    function permit(address owner, address spender, uint amount, uint deadline, uint8 v, bytes32 r, bytes32 s) external {
        bytes32 structHash = keccak256(abi.encode(PERMIT_TYPEHASH, owner, spender, amount, nonces[owner]++, deadline));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAINSEPARATOR, structHash));
        address signatory = ecrecover(digest, v, r, s);
        require(signatory != address(0), "permit: signature");
        require(signatory == owner, "permit: unauthorized");
        require(block.timestamp <= deadline, "permit: expired");

        _approve(owner, spender, amount);

        emit Approval(owner, spender, amount);
    }

    function withdraw(uint256 shares) external returns (uint256) {
        _burn(msg.sender, shares);
        return _withdraw(address(this), msg.sender, _shareValue(shares), true); // `true` = withdraw from `best`
    }

    function migrate() external onlyAffiliate returns (uint256) {
        return _migrate(address(this));
    }

    function _getChainId() internal view returns (uint) {
        uint chainId;
        assembly { chainId := chainid() }
        return chainId;
    }
}
