# OpenROAD GitHub Actions

This repository contains GitHub Actions for usage with the OpenROAD project's
repositories.

## [`security_scan_on_push`](./security_scan_on_push)

This action prevents accidental publishing of private data such as confidential
PDK information.

## [`clone_from`](./clone_from)

This action clones a GitHub repository using https and the GitHub token.

It uses "tree less" clone so that it can be pushed from while not needing the
complete repository contents.

## [`push_to`](./push_to)

This action pushes to a GitHub repository using ssh with
[a deploy key (with write access)](https://docs.github.com/en/developers/overview/managing-deploy-keys#deploy-keys).

Steps for using are;

 1) Generate a new deploy key using the command `ssh-keygen -t ed25519 -f deploy_key`.

 2) Add the private key output (in file `deploy_key`) to the repositories
    [GitHub Actions secrets](https://docs.github.com/en/developers/overview/managing-deploy-keys#deploy-keys).

 3) Add the public key output (in file `deploy_key.pub`) to the repositories
    Deploy Keys making sure to give the key write access.

 4) Add the GitHub Action in your workflow.yml like so;
    ```yaml
        - name: Push to staging repository.
          uses: The-OpenROAD-Project/actions/push_to@main
          with:
            owner: The-OpenROAD-Project
            repo: OpenROAD
            branch: main
            deployKey: ${{ secrets.STAGING_DEPLOY_KEY }}
    ```

## [`remove_label`](./remove_label)

Removes a label from a pull request.

## [`send_pr`](./send_pr)

After a branch has been pushed to the staging repository, automatically create
a pull request from the staging repository to the upstream repository.

## [`link_pr`](./link_pr)

After a pull request has been created from the staging repository to the
upstream repository, this GitHub Actions creates a deployment linking to the
public pull request.

## [`upstream_sync`](./upstream_sync)

Pulls the upstream repository into the local repository.

