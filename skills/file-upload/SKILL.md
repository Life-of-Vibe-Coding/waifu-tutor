---
name: file-upload
description: Classify uploaded file/folder items against existing folders, ask for confirmation, and append only after explicit user approval.
tags: [upload, file, folder, classify, organize, confirmation, workflow, openviking, valkin]
---

# File Upload

## When to use

Use this skill when user uploads files/folders and asks to:

- reason, classify, or group uploaded items
- verify where items belong
- organize only after confirmation

## System of record (critical)

All file operations in this skill are performed on the **Valkin/OpenViking system** (virtual filesystem), not local OS folders.

- Use `viking://resources/users/{user_id}/documents/{doc_id}` as resource scope.
- Folder/subject matching is based on system folders (`list_subjects`) in Valkin-backed app data.
- Do not claim local file move/copy/rename was executed.

## Workflow (mandatory)

### 1) Fetch folder descriptions and reason one-by-one

1. Fetch existing folders from system (`list_subjects`).
2. Fetch uploaded items (`list_recent_uploads`).
3. Reason by name:
   - one file: reason by file name
   - one folder: reason by folder name (`source_folder`)
   - multiple files/folders: reason one by one

### 2) Propose and ask user

- If likely match exists, ask user to confirm the classification.
- If no confident match, suggest folder/file grouping name to user.
- Do not append/organize yet.

### 3) Append only after explicit acceptance

- Append/organize action is allowed only after explicit user confirmation.
- If user does not confirm, continue clarifying and re-proposing.
- Never auto-organize.
- When action is executed, it must target Valkin/OpenViking-backed data flow, not local filesystem actions.

## Additional fallback rules (mandatory)

### A) Files uploaded -> fallback to file content

If no relevant folder is found by file name:

- reason with file content (document chunks/context), then re-classify.

### B) Folder uploaded -> fallback to child file names only

If no relevant folder is found by folder name:

- reason with names of files inside the folder
- do **not** reason with contents of child files

## Input

- Uploaded files/folders: names + ids + optional `source_folder`
- Existing folders in system
- Optional file content context (file-only fallback)

## Output

- One-by-one classification proposal
- For each item:
  - matched folder (if any) or suggested new folder name
  - short reason and reasoning basis (name/content fallback/child-name fallback)
- Explicit confirmation question before any append action

## Boundaries

- If no uploaded items found: ask user to re-upload.
- If no folders exist: propose initial folder names and ask which to create/use.
- If user confirmation is ambiguous: ask clarification; do not append.
