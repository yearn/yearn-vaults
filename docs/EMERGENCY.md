# Emergency Procedures for Yearn Finance

## TLDR: [Emergency Check List](#emergency-checklist)

## Introduction

This document details the emergency procedures and guidelines that should take place during an emergency situation.

The main goal of this document is to help minimize as much as possible a potential loss of funds in yearn platform and Smart Contracts during an emergency situation.

## Definitions and Examples of Emergencies

For the purposes of this document we define emergency situation to be:

**_Any situation that may lead to a considerable amount of loss of funds for yearn users._**

This is a non exhaustive list of possible emergency scenarios:

1. Exploit in Vault/Strategy code that can cause a loss of funds for users
2. Bug in Vault/Strategy code that may cause loss of funds for users
3. An exploit in an underlying protocol that a yearn strategy is utilizing that may lead to loss of funds for the users
4. A bug in an underlying protocol that a yearn strategy is utilizing that may lead to loss of funds for the users
5. A key role like a strategist having the private keys stolen

## Roles

The following roles are identified and should be assigned during an emergency.

- Facilitator
- Strategist Lead
- Multi-sig Operations
- Web Lead
- Core Dev Lead (Guardian)
- Ops

Some of these roles may be done by the same person up to two concurrent roles.

### Facilitator:

The person in this role will facilitate the emergency handling and ensure that the team follows the overall process and engages the correct teams and stakeholders to make the necessary quick decisions. This person can be anybody that is familiar with the process and is confident that he/she can drive the team to accomplish the steps needed. It's expected that this person has some experience either through real scenarios or drill training.

### Multi-sig Operations:

The person in this role will be tasked with ensuring that during the emergency scenario the different yearn teams multi-sig wallets can execute emergency transaction in a timely manner.

Main responsibilities are:

- Help clearing the queue on any pending operations once the War Room starts
- Coordination of required signers so they can respond quickly to the queued transactions
- Preparing or helping with transactions in the different multi-sigs
  (dev.ychad.eth, brain.ychad.eth, ychad.eth)
  Reference:
  - [emergency-toolbox](https://github.com/yearn/emergency-toolbox)
  - [CMO](https://github.com/yearn/chief-multisig-officer)

### Strategist Lead:

This role will be in charge of coordinating quick changes to management and strategist role during the emergency, including but not limited to:

- Strategist Multi-sig transactions and operations
- Set strategy in emergency exit mode
- Update debt ratios
- Remove Strategies from Queue
- Coordinate Harvests

### Core Dev Lead:

This role will be in charge of coordinating quick changes to governance and guardian roles during the emergency, including but not limited to:

- Core Dev Multi-sig transactions and operations
- Revoke a Strategy
- Set vault in emergency shutdown mode

### Web Lead:

This role will be in charge of coordinating quick changes needed on UI including but not limited to:

- Disable deposits/withdraws on UI
- Show alerts on website
- Other UI related work needed during emergency scenarios

### Ops:

This role will be in charge of coordinating comms and operations assistance as needed:

- Clear with war room what information and communication can be published during and after the incident
- Coordinate Comms
- Take note of timelines and events for disclosure

### Emergency Steps

See [Check list](#Emergency-checklist) and [Tools](#tools)

These steps are a guideline to follow when an incident is reported that needs immediate attention.

The primary goal of the team implementing these guidelines is to minimized as much as possible the loss of funds for Yearn Finance users, all decisions made in the session should be driven by this primary goal.

1. The first team member reported should open a private chat room (War Room) with a voice channel and invite only the team members that are online and that can cover the [roles described above](#Roles). The War Room should be limited to members that can provide actions on the roles and additional persons that can help provide insight into the issue.
1. All the information that is gathered during the War Room should be private to the chat and relevant data should be pinned and updated by facilitator for the entire team to have handy.
1. First goal of the War Room is to assess as quickly as possible the situation and confirm the report information and how critical the incident is. A few questions to guide this process:

- Is there confirmation from several team members/sources that the issue report is correct? Can we list sample transactions that expose the incident and Pin in the War Room?
- Is the strategist that knows more about the code in the War Room? can the strategist be reached and if not, can we reach the backup strategist?
- Are funds at risk if the team doesn't take immediate action? (This includes current loss of funds if further losses can take place)
- Does the issue affect several vaults/strategies, can the affected contracts be identified ? Pin the list to War Room.
- Multi sig operations roles should start gathering signers and start clearing the queue for any immediate action needed.
- If there is no risk of loss of funds, does the team still need to take preventive action or some mitigation?
- Is there quorum on the team that the situation is under control to drop the War Room and continue monitoring offline at this point in time?

4. Once the report is confirmed, the next stop is to take immediate corrective action to prevent further loss of funds. If cause of the issue needs further research, team requires to lean on the side of caution and take preventive actions while causes are identified. Here a few questions that can guide the decisions of the team:

- Is pausing deposits in the affected vaults needed? Also remove migrations and deposits from UI?
- Activate emergency exit on the affected strategies?
- Remove one or more strategies from the withdrawal queue from the affected vaults?
- Activate emergency shutdown in the vault?
- Revoke 1 or more strategies?
- Several Team members can confirm the corrective actions will stop the immediate risk through local ganache fork testing? Strategist and Core Dev main roles to confirm this step.

5. The immediate corrective actions should be scripted or taken from the repository [emergency-toolbox](https://github.com/yearn/emergency-toolbox) and executed ASAP. Multi-sig operator and strategist lead should coordinate this execution within the corresponding roles. **NOTE: This step is meant to give the War Room time to assess and research a more long term solution**.

6. Once corrective actions are in place and there is team quorum to confirm there is no further funds at risk, the two next goals are cause identification and possible remediation plans should start taking form. A few questions/actions during this step that can help the team make decisions:

- What communications can be made public at this point in time?
- Can research among members of the War Room be divided? This step can be open for team members to do live debug sessions sharing screens to help identify the problem using the sample transactions.

7. Once the cause has been identified a brain storming session can take place to come up with best remediation plan and implementation of code if needed. A few questions that can help during this time:

- In case there are many possible solutions can team prioritize by weighing each option by time to implement and minimization of losses?
- Can we test the possible solutions and compare end state fixes the cause of the issue?
- There's quorum from the War Room members about the best solution? If not can we identified the objections and work out a path to Quorum taking into account minimization of losses as priority?
- If a solution will take longer than a few hours, are there any further communications and preventive actions needed in the time the solution will be coded?
- Does the solution need a longer term plan, can team identified owners for tasks/steps towards execution of said plan?

8. Once a solution has been implemented, the team will validate the solution fixes the cause of the issue and minimizes the loss of funds as much as possible. Possible actions needed during this step:

- Run in ganache fork simulations of end state to confirm solutions
- Coordinate signatures from multi-sig signers and execution
- Enable UI changes to normalize operations as needed

9. Assign ownership for redacting [disclosure](https://github.com/yearn/yearn-security) and collection of timeline and events.

10. Team Quorum can decide if the War Room can end. Is up to the facilitator to break down the War Room and set reminders if this takes longer than a few hours for members to reconvene.

### Emergency Checklist

This checklist should be complemented with the [steps](#emergency-steps)

- War room with audio created
- Key roles are covered in the War Room
- Strategist or expert related to issue is available or a backup instead
- Is Multi sig queue clear or actions started to clear it
- Issue has been confirmed and identified
- Immediate corrective/preventive actions are put in place and risk of loss of funds prevented
- Communications of current situation
- Research causes
- Brainstorm solutions
- Implement and validate solutions
- Prioritize solutions
- Team Quorum on solution reached
- Coordination and Execution of solution
- Monitoring and incident resolution confirmed
- Assign Disclosure Task and Owner to collect events and timelines
- Disband War Room

### Tools

List of tools and alternatives in case primary tools are not available during incident.

| Description         | Primary                                        |                               Secondary                                |
| ------------------- | ---------------------------------------------- | :--------------------------------------------------------------------: |
| Code Sharing        | Github                                         | [HackMd](https://hackmd.io/), [CodeShare](https://codeshare.io/5Og7mj) |
| Communications      | Telegram                                       |                                Discord                                 |
| Transaction Details | [Etherscan](https://etherscan.io/)             |                    [EthTxInfo](https://ethtx.info/)                    |
| Debugging           | Brownie                                        |                    [Tenderly](https://tenderly.co/)                    |
| Transaction Builder | [ape-safe](https://github.com/banteg/ape-safe) |               Backup if gnosis safe Api is not working??               |
| Screen Sharing      | [jitsi](https://jitsi.org/)                    |                            Google Hangouts                             |

### Incident Post Mortem

This exercise should be conducted after an incident to recollect data from the participants of the War Room to produce as output action items and improvement points to be incorporated into Yearn's process.

A facilitator is a role any person can take that will lead the steps denoted here for the Post Mortem session.

It is recommended that the Post Mortem is conducted at the most a week after the incident so participants have a fresh recollection.

It is key that most of the participants of the War Room are involved during this session to have a correct assessment of the outputs. Discussion is encouraged as long as its focused on process improvement and not finger pointing at any specific members.

Participants are encouraged to provide inputs on each of the steps, if a participant is not giving inputs is the job of the facilitator to help out and ask them.

Expected Outputs from Post Mortem:

- List of what went well during War Room
- List of what can we improve during War Room
- Root Cause Analysis and action items to improve in yearn's finance processes to prevent the incident of ever happening again.
- List of action items with owner's and timelines to execute.

## Steps for Post Mortem

1. Facilitator will run the session in a voice channel and share a screen for all participants to follow.
1. Facilitator collects list of things that went well during the incident War Room from the participants.
1. Facilitator collects list of things that could have been better during the incident War Room from participants.
1. Facilitator runs a root cause analysis exercise clearly writing the problem statement first and confirming with the participants that the problem statement is correct and understood.
1. Root Cause Analysis can be identified with following tools:

- [Brainstorming](https://en.wikipedia.org/wiki/Brainstorming) session with participants
- [5 Whys](https://en.wikipedia.org/wiki/Five_whys)

6. Once Root Causes have been identified, action items can be written and assigned to willing participants that can own the task and execute it. It is recommended that an estimate time be given and a later process can track completion of given assignments. **Note: The action items need to be clear, actionable and measurable for completion**
7. Facilitator or coordinator role tracks completion of action items. The end result of the process should be an actionable improvement in the process. Some possible improvements:

- Changes in the process and documentation
- Changes in code and tests to validate
- Changes in tools implemented and incorporated into the process
