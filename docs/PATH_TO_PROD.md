# Protocol Due Diligence: [ PROTOCOL NAME ]

## Overview + Links
- **[Site](https://google.com)**
- **Team**
- **[Docs](https://google.com)**
- **Audits and due diligence disclosures**

## Rug-ability
**Multi-sig:**

**Number of Multi-sig signers / threshold:**
    
**Upgradable Contracts:**

**Decentralization:**



## Misc Risks

[List any risks pertaining to things like: how yield is generated, governance, multisig, etc]

### Audit Reports / Key Findings

[List links and any key findings]

# Path to Prod

## Strategy Details
- **Description:**
- **Strategy current APR:**
- **Does Strategy delegate assets?:**
- **Target Prod Vault:**
- **BaseStrategy Version #:**
- **Target Prod Vault Version #:**

## Testing Plan
### Ape.tax
- **Will Ape.tax be used?:**
- **Will Ape.tax vault be same version # as prod vault?:**
- **What conditions are needed to graduate? (e.g. number of harvest cycles, min funds, etc):**

## Prod Deployment Plan
- **Suggested position in withdrawQueue?:**
- **Does strategy have any deposit/withdraw fees?:**
- **Suggested debtRatio?:**
- **Suggested max debtRatio to scale to?:**

## Emergency Plan
- **Shutdown Plan:**
- **Things to know:**
- **Scripts / steps needed:**
- **Is it safe to...**
    - call EmergencyShutdown
    - remove from withdrawQueue
    - call revoke and then harvest