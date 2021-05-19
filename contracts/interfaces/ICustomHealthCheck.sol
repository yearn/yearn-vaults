pragma solidity >=0.8.0 <0.9.0;

interface ICustomHealthCheck {
    function check(
        uint256 profit,
        uint256 loss,
        address callerStrategy
    ) external view returns (bool);
}
