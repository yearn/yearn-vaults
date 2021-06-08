pragma solidity >=0.6.0 <0.7.0;

interface ICustomHealthCheck {
    function check(
        uint256 profit,
        uint256 loss,
        uint256 callerStrategy
    ) external view returns (bool);
}
