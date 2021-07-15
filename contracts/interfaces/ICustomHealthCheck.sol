pragma solidity >=0.6.0 <0.7.0;

interface ICustomHealthCheck {
    function check(
        address callerStrategy,
        uint256 profit,
        uint256 loss,
        uint256 debtPayment,
        uint256 debtOutstanding
    ) external view returns (bool);
}
