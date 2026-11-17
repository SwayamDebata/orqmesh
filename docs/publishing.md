# GitHub and Python package launch guide

This guide describes steps for an authorized maintainer. Nothing in this guide automatically creates a repository, uploads a package, or verifies a name. Commands are examples for the maintainer to run after review. **TestPyPI and public GitHub are public disclosures**, even for beta software.

## 1. Decisions and blockers

1. Confirm ownership and permission to publish every part of the code, documentation, examples, and third-party material. A separate account does not override employment, customer, contributor, or confidentiality obligations.
2. The initial public release is licensed under Apache-2.0. The canonical text is in `LICENSE`, and `pyproject.toml` carries the SPDX identifier `Apache-2.0`. Review any required third-party notices before adding them.
3. Check `orqmesh` on the intended Python index and review naming/trademark conflicts. Package-name availability is not trademark clearance and can change. If the name changes, update the distribution name, import package, references, and tests together.
4. Review the intended release for confidential material and secrets: source, docs, examples, configuration, generated artifacts, and, if any history is reused, every commit/branch/tag that will be pushed. The ignore file cannot remove already tracked or previously published data. Avoid carrying an old repository's history into a new account without an explicit review.
5. Private vulnerability reports go to the contact in `SECURITY.md`. Keep supported versions, contribution rules, maintainers, release ownership, and package repository URLs current.
6. Perform a security and functionality review. The SDK is an experimental sequential workflow prototype; local checkpoints are unencrypted and lack concurrent-run protection. Adapter tests currently use fakes, not real provider compatibility matrices.

## 2. Secret and artifact hygiene

The project's `.gitignore` covers common `.env` files, keys/certificates, credential files, checkpoint directories, virtual environments, caches, logs, and build artifacts. It intentionally permits sanitized `.env.example` files; **never put secrets in an example**.

Ignore rules are not a security guarantee: unusual filenames, secrets embedded in code/docs, files already tracked, ignored files added with force, generated distribution contents, and prior commits remain risks. Review what will be staged and the exact build artifacts, use a secret scanner in an authorized environment, and enable GitHub secret scanning and push protection where available. If a credential is exposed, revoke/rotate it immediately; deleting the text is not enough.

Do not upload or copy local `.venv`, `.checkpoints`, `dist`, `build`, `*.egg-info`, or local credentials into a fresh public repository. Existing ignored output may contain stale material from previous builds; build into a fresh release directory and inspect it rather than uploading every artifact in an old `dist` folder.

## 3. Prepare the release version

`pyproject.toml` currently declares distribution name `orqmesh`, import name `orqmesh`, and version `0.1.0b1`. This is a PEP 440 prerelease; it is **not** private. Choose a new version if that version is already present on the target index. Published PyPI filenames/versions cannot be reused after deletion. Keep a changelog and draft release notes describing implemented behavior and limitations.

Do not enter personal account names, fake repository URLs, credential values, or author information into metadata until you have the correct approved details. Once the public repository and website exist, add accurate `project.urls` entries in `pyproject.toml`.

## 4. Build and verify locally

From the project root, in a Python 3.11+ virtual environment:

```powershell
python -m pip install -e ".[dev,release]"
python -m pytest
python -m ruff check .
python -m build --outdir .\dist\release-check
python -m twine check .\dist\release-check\*
```

Use a new, empty release directory or explicitly inspect/clean it yourself before building; `build` does not guarantee removal of older unrelated distributions. Verify the wheel and source archive names/versions and inspect their **contents**, not just the directory listing. For example:

```powershell
python -m zipfile -l .\dist\release-check\orqmesh-0.1.0b1-py3-none-any.whl
python -m tarfile -l .\dist\release-check\orqmesh-0.1.0b1.tar.gz
```

Replace filenames for the chosen version. Check that the wheel contains `orqmesh/py.typed`, intended modules and metadata, and no credentials, local checkpoints, unwanted proprietary files, or stale package names. Inspect the source archive separately: it can contain files not present in the wheel.

Test the built wheel in a separate clean environment, not the editable development environment. The following is an example; use the full path to the exact reviewed wheel and a new folder for the venv:

```powershell
py -3.11 -m venv .\wheel-smoke-venv
.\wheel-smoke-venv\Scripts\python.exe -m pip install --no-deps C:\path\to\orqmesh-0.1.0b1-py3-none-any.whl
.\wheel-smoke-venv\Scripts\python.exe -c "from orqmesh import Workflow, WorkflowStep; print('Orqmesh import OK')"
```

`C:\path\to\...` is a placeholder: substitute the actual reviewed wheel path. The smoke-test venv must not be added to the repository; remove it yourself after the test. Prefer a temp directory outside the repository. Run the package test matrix in CI on the versions declared in metadata; a local test on one interpreter alone does not establish support across all versions.

## 5. Create the separate GitHub repository

After the blockers are cleared:

1. Sign in to the intended GitHub account yourself; enable two-factor authentication. Create a repository with the chosen approved name. Start **private** while reviewing, and do not initialize it with conflicting files if you plan to push a locally created repository.
2. Prefer a fresh, reviewed source export/new repository if you do not want to carry previous history. Copy only files approved for release; exclude ignored local artifacts and credentials. Confirm the export contains the authorized license and correct ownership information.
3. Initialize and commit the reviewed files in that **new source directory**. The placeholders below must be replaced with your actual repository URL and branch name:

```powershell
git init
git branch -M main
# Stage individually reviewed files and directories rather than blindly adding everything.
git add README.md pyproject.toml CHANGELOG.md CONTRIBUTING.md SECURITY.md .gitignore .github docs examples src tests
# After adding the authorized LICENSE file, stage it explicitly too.
git diff --cached --name-only
git diff --cached
git commit -m "Initial Orqmesh release candidate"
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

`YOUR-ACCOUNT` and `YOUR-REPOSITORY` are placeholders. Review staged paths **and content** before committing. `src` must not contain stale `*.egg-info` artifacts; ignore rules help but do not protect already tracked files. Use GitHub's authentication flow or credential manager; do not put tokens in URLs or commands. If a repository already exists locally, do not overwrite its configuration or push its history without a separate review.

4. In repository settings, enable branch protection/rulesets as appropriate, security alerts and secret scanning/push protection where available, and review Actions permissions. Confirm CI passes on the new repository's default branch. Configure private vulnerability reporting and update the security document.
5. When rights, security, and content review are complete, choose whether to make the repository public. A private repo and a public repository have different sharing risks; check organization/account policies.

## 6. Test package distribution

### Local-only first

Install the reviewed wheel into a separate test environment as above. This does not publish a package and is the safest first integration test. For a shared beta, use an approved private index or repository with appropriate access controls.

### TestPyPI (public)

Only after public distribution is authorized, create a separate TestPyPI account, enable two-factor authentication, and verify that the approved name/version is available on TestPyPI. TestPyPI and PyPI are separate services and accounts. Upload only the two exact reviewed artifacts in the fresh release directory, not every file in an old `dist` directory:

```powershell
python -m twine upload --repository testpypi .\dist\release-check\orqmesh-0.1.0b1-py3-none-any.whl .\dist\release-check\orqmesh-0.1.0b1.tar.gz
```

Use the appropriate filenames if the version changes. Authenticate via an approved secure mechanism; never place tokens in a command, source file, issue, or repository. When prompted for a secret, type it directly into the terminal. Once uploaded, test the exact prerelease from TestPyPI in a new environment:

```powershell
python -m pip install --index-url https://test.pypi.org/simple/ --no-deps "orqmesh==0.1.0b1"
python -c "import orqmesh; print(orqmesh.__file__)"
```

`--no-deps` is reasonable for this core package because it currently has no mandatory runtime dependencies; it does not install optional integrations. Confirm the installed version and review the TestPyPI project page before proceeding. Public beta artifacts and metadata are visible to everyone.

## 7. Publish to PyPI

After public release approval and successful clean-install/metadata tests, ensure the approved name/version is available on PyPI and upload the **same reviewed artifacts** (if metadata changes, rebuild and re-review):

```powershell
python -m twine upload .\dist\release-check\orqmesh-0.1.0b1-py3-none-any.whl .\dist\release-check\orqmesh-0.1.0b1.tar.gz
```

Use the exact new version and filenames. Verify the package page and install the exact version in a fresh environment. Users must explicitly request a beta version or use pip's prerelease selection rules; a prerelease is not necessarily installed by an unpinned default command. Published versions are immutable: fix a release with a new version, not by overwriting artifacts.

## 8. Optional: secure GitHub Actions Trusted Publishing

The current CI only tests/lints/builds; **no publishing workflow is configured**. For repeatable releases, prefer PyPI Trusted Publishing (short-lived OIDC tokens) to committed or long-lived API tokens. After the repository and account details are final:

1. Create separate TestPyPI and PyPI accounts/projects or configure **pending publishers** for a new project.
2. Register the exact GitHub repository owner, repository name, and publishing workflow **filename** on each index. Configure matching GitHub environment names, e.g. `testpypi` and `pypi`; protect the PyPI environment with required reviewers where available.
3. Add a dedicated reviewed release workflow with a build job that runs tests/builds and uploads artifacts, and a separate publishing job that downloads only those artifacts. Give the publishing job `id-token: write` for OIDC and restrict it to approved release events/environment. Do not run builds inside the publishing job.
4. Configure the TestPyPI upload endpoint for the test job. Use a protected tag/release process for PyPI, verify tag and package version match, and review/pin third-party actions to trusted commit SHAs where your security policy requires.
5. Run TestPyPI first; inspect artifacts and approvals before enabling the PyPI job. See the [official Python Packaging guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) and [PyPI trusted publisher documentation](https://docs.pypi.org/trusted-publishers/).

An action workflow is deliberately not generated here: the actual account, repository, environment protections, and approved trigger are not yet known. Never store PyPI credentials in the repository.

## 9. Final release checklist

- [ ] Ownership, public distribution, third-party notices, and open-source license approved; canonical license and metadata added.
- [ ] Name/trademark reviewed; intended index name and version controlled.
- [ ] Review source, current export, docs, examples, artifacts, and any history/branches that will be published; scan for secrets and rotate any exposures.
- [ ] Private vulnerability-reporting channel established; security/support/contribution guidance updated.
- [ ] Tests, lint, package build, metadata check, artifact inspection, and clean wheel installation pass.
- [ ] Supported Python and integration matrix verified; limitations documented without production-readiness claims.
- [ ] Repository settings, access, CI, branch protections, and environment approvals reviewed.
- [ ] Public beta upload and exact-version install verified on TestPyPI if authorized.
- [ ] Reviewed artifacts published to PyPI only after release sign-off; release notes and tag recorded.
