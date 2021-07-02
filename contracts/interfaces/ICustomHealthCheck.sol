pragma solidity >=0.6.0 <0.7.0;

interface ICustomHealthCheck {
    function check(
        uint256 profit,
        uint256 loss,
        address callerStrategy
    ) external view returns (bool);
}
