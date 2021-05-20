# Emergency Procedures for Yearn Finance

## TLDR: [Emergency Checklist](#emergency-checklist)

## Introduction

This document details the procedures and guidelines that should take place in the event of an emergency situation. Its purpose is to minimize the risk for loss of funds for Yearn's users, Treasury, and Smart Contracts.

## Definitions and Examples of Emergencies

For the purposes of this document, an emergency situation is defined to be:

**_Any situation that may lead to a considerable amount of loss of funds for Yearn users, Yearn's Treasury, or Smart Contracts deployed by Yearn._**

This is a non exhaustive list of possible emergency scenarios:

1. Bug/Exploit in Vault/Strategy code that can cause a loss of funds for users
2. Bug/Exploit in an underlying protocol that a Yearn Strategy is utilizing that may lead to loss of funds
3. Loss of private keys for a key role, such as a Strategist
4. Potential exploit discovered by team or bounty program researcher
5. Active exploit / hack in progress discovered by unknown party

## Roles

In the event of an emergency situation, the following roles should be assigned to Yearn contributors working to resolve the situation:

- Facilitator
- Multi-sig Herder
- Strategist Lead
- Core Dev Lead (Guardian)
- Web Lead
- Ops

A contributor may be assigned up to two of these roles concurrently.

### Facilitator

Facilitates the emergency handling and ensures the process described in this document is followed, engaging with the correct stakeholders and teams in order for the necessary decisions to be made quickly. A suitable Facilitator is any person familiar with the process and is confident that they can drive the team to follow through. It's expected that the person assigned to this role has relevant experience either from having worked real scenarios or through drill training.

### Multi-sig Herder

Responsible for ensuring that different Yearn teams' Multi-sig wallets (i.e. dev.ychad.eth, brain.ychad.eth, ychad.eth) are able to execute transactions in a timely manner during the emergency.

Main responsibilities:

- Help clear the queue of any pending operations once the War Room starts
- Coordinate required signers so they can respond quickly to queued transactions
- Prepare or help with transactions in different multi-sigs
  Reference:
  - [emergency-toolbox](https://github.com/yearn/emergency-toolbox)
  - [CMO](https://github.com/yearn/chief-multisig-officer)
  - [strategists-ms](https://github.com/poolpitako/strategists-ms)

### Strategist Lead

In charge of coordinating quick changes to management and strategist roles during the emergency, including but not limited to:

- Prepare and Execute Strategist Multi-sig transactions and operations
- Set strategy in emergency exit mode
- Update debt ratios
- Remove Strategies from Queue
- Coordinate Harvests

### Core Dev Lead (Guardian)

Coordinates quick changes to Governance and Guardian roles during the emergency, including but not limited to:

- Prepare and Execute Core Dev Multi-sig transactions and operations
- Revoke a Strategy
- Set vault in emergency shutdown mode

### Web Lead

Coordinates quick changes to UI and Websites as required, including but not limited to:

- Disable deposits/withdrawals through the UI
- Display alerts and banners
- Other UI related work

### Ops

In charge of coordinating comms and operations assistance as required:

- Clear with War Room what information and communication can be published during and after the incident
- Coordinate Communications
- Take note of timelines and events for disclosure

## Emergency Steps

_Also see [Check list](#Emergency-checklist) and [Tools](#tools)._

This acts as a guideline to follow when an incident is reported requiring immediate attention.

The primary objective is minimized the loss of funds, in particular for Yearn's users. All decisions made should be driven by this goal.

1. Open a private chat room (War Room) with a voice channel and invite only the team members that are online that can cover the [roles described above](#Roles). The War Room is limited to members that act in the capacities of the designated roles, as well as additional persons that can provide critical insight into the circumstances of the issue and how it can best be resolved.
2. All the information that is gathered during the War Room should be considered private to the chat and not to be shared with third parties. Relevant data should be pinned and updated by the Facilitator for the team to have handy.
3. The team's first milestone is to assess the situation as quickly as possible: Confirming the reported information and determine how critical the incident is. A few questions to guide this process:
   - Is there confirmation from several team members/sources that the issue is valid? Are there example transactions that show the incident occurring? (Pin these in the War Room)
   - Is the Strategist that knows the most about the code in the War Room? Can the Strategist in question be reached? If not, can we reach the backup Strategist?
   - Are funds presently at risk? Is immediate action required?
   - Is the issue isolated or does it affect several vaults/strategies? Can the affected contracts be identified? (Pin these in the War Room)
   - Which Multi-sig will require signing to address the issue? The Multi-sig Herder should begin to notify signers and clear the queue in preparation for emergency transactions.
   - If there is no immediate risk for loss of funds, does the team still need to take preventive action or some other mitigation?
   - Is there agreement in the team that the situation is under control and that the War Room can be closed?
4. Once the issue has been confirmed as valid, the next stop is to take immediate corrective action to prevent further loss of funds. If root cause requires further research, the team must err on the side of caution and take emergency preventive actions while the situation continues to be assessed. A few questions to guide the decisions of the team:
   - Disable deposits to the affected Vaults? Should migrations and deposits be removed from the UI?
   - Activate Emergency Exit on the affected Strategies?
   - Remove one or more strategies from the withdrawal queue from the affected vaults?
   - Activate Emergency Shutdown in the Vault?
   - Revoke 1 or more Strategies?
   - Are multiple Team members able to confirm the corrective actions will stop the immediate risk through local Ganache fork testing? Strategist and Core Dev main roles in particular to confirm this step.
5. The immediate corrective actions should be scripted or taken from the repository [emergency-toolbox](https://github.com/yearn/emergency-toolbox) and executed ASAP. Multi-sig Herder and Strategist Lead should coordinate this execution within the corresponding roles. **NOTE: This step is meant to give the War Room time to assess and research a more long term solution**.
6. Once corrective measures are in place and there is confirmation by multiple sources that funds are no longer at risk, the next objective is to identify the root cause. A few questions/actions during this step that can help the team make decisions:
   - What communications should be made public at this point in time?
   - Can research among members of the War Room be divided? This step can be open for team members to do live debug sessions sharing screens to help identify the problem using the sample transactions.
7. Once the cause is identified, the team can brainstorm to come up with the most suitable remediation plan and its code implementation (if required). A few questions that can help during this time:
   - In case there are many possible solutions can the team prioritize by weighing each option by time to implement and minimization of losses?
   - Can the possible solutions be tested and compared to confirm the end state fixes the issue?
   - Is there agreement in the War Room about the best solution? If not, can the objections be identified and a path for how to reach consensus on the approach be worked out, prioritizing the minimization of losses?
   - If a solution will take longer than a few hours, are there any further communications and preventive actions needed while the fix is developed?
   - Does the solution require a longer term plan? Is there identified owners for the tasks/steps for the plan's execution?
8. Once a solution has been implemented, the team will confirm the solution resolves the issue and minimizes the loss of funds. Possible actions needed during this step:
   - Run in ganache fork simulations of end state to confirm the proposed solution(s)
   - Coordinate signatures from multi-sig signers and execution
   - Enable UI changes to normalize operations as needed
9. Assign a lead to prepare a [disclosure](https://github.com/yearn/yearn-security) (should it be required), preparing a timeline of the events that took place.
10. The team agrees when the War Room can be dismantled. The Facilitator breaks down the War Room and sets reminders if it takes longer than a few hours for members to reconvene.

### Emergency Checklist

This checklist should be complemented with the [steps](#emergency-steps)

- [ ] Create War room with audio
- [ ] Assign Key Roles to War Room members
- [ ] Add Strategist or other Expert (or their backup) to the War Room
- [ ] Clear related Multi-sig queues
- [ ] Disable deposits and/or withdrawals as needed in the web UI
- [ ] If share price has been artificially lowered, then call `vault.setDepositLimit(0)` from governance
- [ ] Confirm and identify Issue
- [ ] Take immediate corrective/preventive actions in order to prevent (further) loss of funds
- [ ] Communicate the current situation internally and externally (as appropriate)
- [ ] Determine the root cause
- [ ] Propose workable solutions
- [ ] Implement and validate solutions
- [ ] Prioritize solutions
- [ ] Reach agreement in Team on best solution
- [ ] Execute solution
- [ ] Confirm incident has been resolved
- [ ] Assign ownership of security disclosure report
- [ ] Disband War Room
- [ ] Conduct immediate debrief
- [ ] Schedule a Post Mortem

### Tools

List of tools and alternatives in case primary tools are not available during an incident.

| Description         | Primary                                        |                               Secondary                                |
| ------------------- | ---------------------------------------------- | :--------------------------------------------------------------------: |
| Code Sharing        | Github                                         | [HackMd](https://hackmd.io/), [CodeShare](https://codeshare.io/5Og7mj) |
| Communications*      | Telegram                                       |                                Discord                                 |
| Transaction Details | [Etherscan](https://etherscan.io/)             |                    [EthTxInfo](https://ethtx.info/)                    |
| Debugging           | Brownie                                        |                    [Tenderly](https://tenderly.co/)                    |
| Transaction Builder | [ape-safe](https://github.com/banteg/ape-safe) |               _Backup if gnosis safe Api is not working?_               |
| Screen Sharing*      | [jitsi](https://jitsi.org/)                    |                            Google Hangouts                             |


**Facilitator is responsible to ensure no unauthorized persons enter the War Room or join these tools via invite links that leak.**

## Incident Post Mortem

A Post Mortem should be conducted after an incident to gather data and feedback from War Room participants in order to produce actionable improvements for Yearn processes such as this one.

Following the dissolution of a War Room, the Facilitator should ideally conduct an immediate informal debrief to gather initial notes before they are forgotten by participants. 

This can then be complemented by a more extensive Post Mortem as outlined below.

The Post Mortem should be conducted at the most a week following the incident to ensure a fresh recollection by the participants.

It is key that most of the participants of the War Room are involved during this session in order for an accurate assessment of the events that took place. Discussion is encouraged. The objective is to collect constructive feedback for how the process can be improved, **and not** to assign blame on any War Room participants.

Participants are encouraged to provide inputs on each of the steps. If a participant is not giving inputs, the Facilitator is expected to try to obtain more feedback by asking questions.

### Post Mortem Outputs

- List of what went well
- List of what be improved
- List of questions that came up in the Post Mortem
- List of insights from the process
- Root Cause Analysis along with concrete measures required to prevent the incident from ever happening again.
- List of action items assigned to owners with estimates for completion.

### Post Mortem Steps

1. Facilitator runs the session in a voice channel and shares a screen for participants to follow notes.
2. Facilitator runs through an agenda to obtain the necessary [outputs](#post-mortem-outputs).
3. For the Root Cause Analysis part, the Facilitator conducts an exercise to write the problem statement first and then confirm with the participants that the statement is correct and understood.
4. Root Cause Analysis can be identified with following tools:
   - [Brainstorming](https://en.wikipedia.org/wiki/Brainstorming) session with participants
   - [5 Whys Technique](https://en.wikipedia.org/wiki/Five_whys)
5. Once Root Causes have been identified, action items can be written and assigned to willing participants that can own the tasks. It is recommended that an estimated time for completion is given. A later process can track completion of given assignments. **Note: The action items need to be clear, actionable and measurable for completion**
6. The Facilitator tracks completion of action items. The end result of the process should be an actionable improvement in the process. Some possible improvements:
   - Changes in the process and documentation
   - Changes in code and tests to validate
   - Changes in tools implemented and incorporated into the process
