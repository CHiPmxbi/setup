# CHiPmxbi Setup

用于配置和准备 mxbi Raspberry Pi 实验工作站的工具集合。

该仓库应在控制机上运行，包含两个相互独立的部分：

- `ansible/` 声明式管理所有 mxbi 工作站的共享状态。
- `tools/` 提供不适合 Ansible 的设备级交互式工具。

## 前置条件

控制机需要安装 Ansible，并且能够通过 SSH 连接目标 Raspberry Pi。目标账户必须是
具有 sudo 权限的非 root 用户，其 GitHub SSH 公钥必须已经注册到 GitHub。

```nu
brew install ansible
cd ansible
ansible-galaxy collection install -r requirements.yml
```

## 配置

创建 inventory 和加密的 Vault 变量：

```nu
cp inventory/hosts.yml.example inventory/hosts.yml
cp vault/mxbi/github.yml.example vault/mxbi/github.yml
ansible-vault encrypt vault/mxbi/github.yml
ansible-vault edit vault/mxbi/github.yml
```

执行前编辑 `inventory/hosts.yml`，再通过 `ansible-vault edit` 替换
`vault_github_ssh_private_key` 中的占位内容。禁止将私钥以明文写入或提交到仓库。本地
`vault/mxbi/github.yml` 已被 Git 忽略，并且仅由 `github` tag 加载。

完整配置默认启用 cogmoteGO email。先在 `roles/mxbi/defaults/main.yml` 中设置
`mxbi_cogmotego_email_address`、`mxbi_cogmotego_email_smtp_host` 和
`mxbi_cogmotego_email_smtp_port`，再创建并加密密码 Vault：

```nu
cp vault/mxbi/cogmotego_email.yml.example vault/mxbi/cogmotego_email.yml
ansible-vault encrypt vault/mxbi/cogmotego_email.yml
ansible-vault edit vault/mxbi/cogmotego_email.yml
```

将 `vault_cogmotego_email_password` 替换为真实邮件密码。该模块不会读取或修改
cogmoteGO recipients，并会在保存密码前准备 login keyring。

可选的 Samba 挂载模块使用独立 Vault。创建并加密密码文件：

```nu
cp vault/mxbi/samba.yml.example vault/mxbi/samba.yml
ansible-vault encrypt vault/mxbi/samba.yml
ansible-vault edit vault/mxbi/samba.yml
```

将 `vault_samba_password` 替换为 `anw-mxbisetup` 的真实密码。Samba Vault 仅在显式使用
`samba` tag 时加载。

Inventory 中的主机名直接使用 OpenSSH 别名。当前 `~/.ssh/config` 通过 `Host mxbi*`
统一提供 `HostName %h.local`、用户 `pi` 和 `IdentityFile ~/.ssh/mxbi`，因此 inventory
无需重复连接参数：

```yaml
mxbi:
  hosts:
    mxbi1:
    mxbi2:
```

inventory 启用了 `StrictHostKeyChecking=accept-new`：Ansible 首次连接未知主机时会自动记录其密钥；已记录主机的密钥发生变化时则会失败。

## 配置目标机

```nu
ansible-playbook site.yml --ask-vault-pass
```

Playbook 会配置系统软件、HiFiBerry Amp2、Linuxbrew、GitHub SSH、Zsh、
cogmoteGO 及其 email、MediaMTX 和 Raspberry Pi VNC。首次完成后可再次以检查模式运行，
确认配置具备幂等性：

```nu
ansible-playbook site.yml --ask-vault-pass --check --diff
```

## 选择性执行

查看可用的功能 tags：

```nu
ansible-playbook site.yml --list-tags
```

在测试机上执行一个或多个功能：

```nu
ansible-playbook site.yml --limit mxbi1 --tags shell
ansible-playbook site.yml --limit mxbi1 --tags 'system,homebrew'
ansible-playbook site.yml --limit mxbi1 --tags github --ask-vault-pass
ansible-playbook site.yml --limit mxbi5 --tags cogmotego_email --ask-vault-pass
ansible-playbook site.yml --limit mxbi5 --tags samba --ask-vault-pass
```

可用 tags 包括 `system`、`hifiberry`、`homebrew`、`github`、`shell`、
`cogmotego`、`cogmotego_email`、`mediamtx`、`desktop` 和 `samba`。
平台校验与用户变量初始化使用 `always` tag，因此每次选择性执行都会运行。`samba`
同时使用特殊的 `never` tag，默认完整配置不会执行它；只有显式选择 `samba` 时，才会
加载 Samba Vault 并将
`//infortrend-storage/Neurowissenschaften/AuditorischeNeurowissenschaften/Projekte/MXBI/data/<主机名>`
挂载到 `/home/pi/server`。

## 交互式工具

`tools/` 是独立的 uv 项目，用于设备特定的交互式配置。

```nu
cd tools
uv run setup_mxbi.py --help
uv run setup_samba_server.py --help
```

Ansible 配置过程不依赖这些工具。
