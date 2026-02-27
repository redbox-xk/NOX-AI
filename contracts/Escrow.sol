// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Escrow is ReentrancyGuard, Ownable {
    struct Record {
        address depositor;
        address token;
        uint256 amount;
        bool released;
        bool refunded;
    }

    mapping(bytes32 => Record) public escrows;

    function deposit(bytes32 id, address token, uint256 amount) external nonReentrant {
        require(escrows[id].amount == 0, "exists");
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        escrows[id] = Record(msg.sender, token, amount, false, false);
    }

    function release(bytes32 id, address recipient) external onlyOwner nonReentrant {
        Record storage r = escrows[id];
        require(!r.released && !r.refunded, "invalid");
        r.released = true;
        IERC20(r.token).transfer(recipient, r.amount);
    }

    function refund(bytes32 id) external onlyOwner nonReentrant {
        Record storage r = escrows[id];
        require(!r.released && !r.refunded, "invalid");
        r.refunded = true;
        IERC20(r.token).transfer(r.depositor, r.amount);
    }
}
