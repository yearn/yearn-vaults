# Contribution guide

If you are new to [Yearn Finance](https://yearn.finance/), you might want to familiarize yourself with its [core concepts and products](https://docs.yearn.finance/). You can also join the [discord channel](https://discord.com/invite/6PNv2nF/) if you have questions or to keep up with updates.

## Setting up your environment

Before proceeding, please set up your environment by following these installation, building and testing [instructions](https://github.com/iearn-finance/yearn-vaults/blob/master/README.md).

## Making your first contribution

Each time you begin a set of changes, ensure that you are working on a new branch that you have created as opposed to the `master` of your local repository. By keeping your changes segregated in this branch, merging your changes into the main repository later will be much simpler for the team.

To create a local branch for `git` to checkout, issue the command:

```bash
git checkout -b feature-in-progress-branch
```

To checkout a branch you have already created:

```bash
git checkout feature-in-progress-branch
```

### Preparing your commit

The official yearn-vaults repository may have changed since the time you cloned it. To fetch changes to the yearn-vaults repository since your last session:

```bash
git fetch origin
```

Then synchronize your master branch:

```bash
git pull origin master
```

To stage the changed files that are be committed, issue the command:

```bash
git add --all
```

Once you are ready to make a commit, you can do so with:

```bash
git commit  -m “fix: message to explain what the commit covers”
```

**NOTE**: commit message must follow Conventional Commits [standard](https://www.conventionalcommits.org/en/v1.0.0/), otherwise your pull requests (discussed further below below) will not pass validation tests. You can use the [`--amend` flag](https://git-scm.com/docs/git-commit) to effectively change your commit message.

### Handling conflicts

If there are conflicts between your edits and those made by others since you started work Git will ask you to resolve them. To find out which files have conflicts, run:

```bash
git status
```

Open those files, and you will see lines inserted by Git that identify the conflicts:

```text
<<<<<< HEAD
Other developers’ version of the conflicting code
======
Your version of the conflicting code
'>>>>> Your Commit
```

The code from the yearn-vaults repository is inserted between `<<<` and `===` while the change you have made is inserted between `===` and `>>>>`. Remove everything between `<<<<` and `>>>` and replace it with code that resolves the conflict. Repeat the process for all files listed by Git status to have conflicts.

When you are ready, use git push to move your local copy of the changes to your fork of the repository on Github.

```bash
git push git@github.com:<your_github_username>/yearn-vaults.git feature-in-progress-branch
```

### Opening a pull request

Navigate to your fork of the repository on Github. In the upper left where the current branch is listed, change the branch to your newly created one (feature-in-progress-branch). Open the files that you have worked on and ensure they include your changes.

Navigate to yearn-vault [repository](https://github.com/iearn-finance/yearn-vaults) and click on the new pull request button. In the “base” box on the left, leave the default selection “base master”, the branch that you want your changes to be applied to. In the “compare” box on the right, select the branch containing the changes you want to apply. You will then be asked to answer a few questions about your pull request. Pull requests should have enough context about what you are working on, how you are solving a problem, and reference all necessary information for your reviewers to help.

After you complete the questionnaire, the pull request will appear in the [list](https://github.com/iearn-finance/yearn-vaults/pulls) of pull requests.

### Following up

Core developers may ask questions and request that you make edits. If you set notifications at the top of the page to “not watching,” you will still be notified by email whenever someone comments on the page of a pull request you have created. If you are asked to modify your pull request, edit your local branch, push up your fixes, then leave a comment to notify the original reviewer that the pull request is ready for further review.
