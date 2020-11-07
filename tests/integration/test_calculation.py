PRECISION = 0.01  # 1%


def tolerance(expected, real):
    return abs(expected - real) / real


def test_calculations(chain, token, vault, new_strategy, andre, keeper, whale):
    whale  # NOTE: Without importing this, there is no deposits in vault
    total = token.balanceOf(vault)

    strategies = []
    # 1/6 + 1/3 + 1/2 = 1
    strategies.append(new_strategy(debt_limit=total // 6, perf_fee=65, seed_debt=True))
    strategies.append(new_strategy(debt_limit=total // 3, perf_fee=50, seed_debt=True))
    strategies.append(new_strategy(debt_limit=total // 2, perf_fee=35, seed_debt=True))

    # Each strategy's debt limits ratios
    debt_ratios = tuple(vault.strategies(s)[2] / vault.debtLimit() for s in strategies)

    # Each strategy's expected returns (actually used to realize returns in test)
    rates = (0.0003, 0.0005, 0.0007)

    # Each strategy's combined governance + strategist performance fee (adjusted from bps)
    perf_fees = tuple(
        (vault.strategies(s)[0] + vault.performanceFee()) / 10_000 for s in strategies
    )

    # The total expected yearly apy for the Vault (debt-weighted sum)
    vault_apy = sum(
        dr * (365 * r - pf) for dr, r, pf in zip(debt_ratios, rates, perf_fees)
    )

    # Don't forget to account for the management fee! (adjusted from bps)
    vault_apy -= vault.managementFee() / 10_000

    # NOTE: Raw is about 20% APY, fee total shaves about 6%
    assert tolerance(vault_apy, 0.13733) < PRECISION

    for day in range(1, 365 + 1):  # 1 harvest a day for each strat, over 1 year
        for strategy, rate in zip(strategies, rates):
            # 3 strategies, harvested once per day (6300 blocks) at equal intervals
            chain.mine(2100, timestamp=chain.time() + 8 * 60 * 60)

            # Simulate "earning" a yield
            expected_return = vault.expectedReturn(strategy)
            realized_return = rate * token.balanceOf(strategy)
            token.mint(strategy, realized_return, {"from": andre})
            strategy.harvest({"from": keeper})

            # Measure Strategy returns
            blocknum = len(chain)
            realized_return = realized_return / 10 ** vault.decimals()
            expected_return = expected_return / 10 ** vault.decimals()
            apy_12d_ema, apy_50d_ema = vault.strategies(strategy)[-2:]

            print(f"[d{day:03d}-b{blocknum:07d}]   Strat: {strategy.address}")
            print(f"[d{day:03d}-b{blocknum:07d}]  Return: {realized_return}")
            print(f"[d{day:03d}-b{blocknum:07d}]    E[R]: {expected_return}")
            print(f"[d{day:03d}-b{blocknum:07d}] 12d EMA: {apy_12d_ema}")
            print(f"[d{day:03d}-b{blocknum:07d}] 50d EMA: {apy_50d_ema}")

            if day > 12:
                assert tolerance(float(apy_12d_ema), realized_return) < PRECISION
            if day > 50:
                assert tolerance(float(apy_50d_ema), realized_return) < PRECISION

        # Measure Vaults returns
        blocknum = len(chain)
        share_price = vault.pricePerShare() / 10 ** vault.decimals()
        expected_price = 1 + vault_apy * day / 365
        apy_12d_ema = vault.apy12dEMA()
        apy_50d_ema = vault.apy50dEMA()

        print(f"[d{day:03d}-b{blocknum:07d}]   Vault: {vault.address}")
        print(f"[d{day:03d}-b{blocknum:07d}]   Price: {share_price}")
        print(f"[d{day:03d}-b{blocknum:07d}]    E[P]: {expected_price}")
        print(f"[d{day:03d}-b{blocknum:07d}] 12d EMA: {apy_12d_ema}")
        print(f"[d{day:03d}-b{blocknum:07d}] 50d EMA: {apy_50d_ema}")

        if day > 3:
            assert tolerance(share_price, expected_price) < PRECISION
        if day > 12:
            assert tolerance(float(apy_12d_ema), vault_apy) < PRECISION
        if day > 50:
            assert tolerance(float(apy_50d_ema), vault_apy) < PRECISION
