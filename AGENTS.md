# Instructions for AI agents

These instructions apply to any AI agent or coding assistant working in
AllStarLink repositories. They implement
[ASL003 - AI Use Practice](https://allstarlink.org/ai/)
([canonical text](https://github.com/AllStarLink/Standards/blob/main/ASL003-AI_Use_Practice.md)).
If anything here conflicts with ASL003, ASL003 wins.

The human you are working for is the author and is responsible for everything
submitted. Your job is to help them produce work they can understand, test, and
defend.

## Rules

- **Follow ASL003.** Read it if you have not.
- **No unattended actions.** Never open issues, post comments, submit pull
  requests, or send messages to project channels without a human reviewing the
  content first. Prepare drafts for the human instead.
- **Attribution.** When creating commits with any AI involvement, add this
  trailer:

  ```
  Assisted-by: <tool name> <model or version>
  ```

  Do NOT add `Co-Authored-By` trailers or otherwise list an AI as author or
  copyright holder.
- **Pull request template.** Fill in the AI Use Disclosure section truthfully.
  Leave the Contributor Attestation boxes UNCHECKED for the human to check;
  only the human can attest.
- **Stay in scope.** Do not make bulk or drive-by changes outside the requested
  task, such as mass refactors, style rewrites, or whitespace cleanup.
- **Verify.** Build, run, and test changes. Verify that APIs, functions,
  packages, and configuration options you use actually exist.
- **Reviews are between humans.** Do not draft review replies for the human to
  post without their reading and understanding them.
- **Confidentiality.** Never put secrets, credentials, personal data, or
  non-public node or user information into prompts, code, or commits.
- **Security issues.** Do not describe suspected vulnerabilities in public
  issues, pull requests, or commits. Tell the human to use the private
  reporting channel in [SECURITY.md](https://github.com/AllStarLink/.github/blob/main/SECURITY.md).
