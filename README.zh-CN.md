# CHiPmxbi Setup

用于配置和准备 mxbi Raspberry Pi 实验工作站的工具集合。

该仓库应在控制机上运行；顶层 Ansible playbook 管理所有 mxbi 工作站的共享状态和实验部署。

## 前置条件

控制机需要安装 Ansible，并且能够通过 SSH 连接目标 Raspberry Pi。目标账户必须是
具有 sudo 权限的非 root 用户，其 GitHub SSH 公钥必须已经注册到 GitHub。

```nu
brew install ansible
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
cogmoteGO recipients，并会在保存密码前准备 login keyring。订阅者由实验部署 playbook 的组变量管理。

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
挂载启动后，`/home/pi/server` 会以 `mxbi-server` 名称加入 cogmoteGO 的可信 Samba root，并重启
cogmoteGO 用户服务。

## 部署实验

`experiment.yml` 是独立于 `site.yml` 的实验部署入口。它假定 Samba、GitHub SSH、
cogmoteGO 和 uv 已由既有环境准备好；不会重新配置这些组件。

库存中的实验组位于 `mxbi_experiments` 下。`group1` 包含 `mxbi1` 到 `mxbi5`，并部署
`GNGSiD`；`group2` 包含 `mxbi6` 到 `mxbi10`，并部署 `self-initiated-discriminate`。
组名与实验名相互独立。每个实验组对应一个组变量文件，例如 `group_vars/group1.yml`：

```yaml
mxbi_experiment_name: GNGSiD
mxbi_experiment_repository: git@github.com:CHiPmxbi/GNGSiD.git
mxbi_experiment_cogmotego_email_recipients:
  - YHu@dpz.eu
```

将仓库地址替换为实际地址后运行：

```nu
ansible-playbook experiment.yml --limit group1
ansible-playbook experiment.yml --limit mxbi1 --check --diff
```

Playbook 会先将 `git@github.com:CHiPmxbi/mxbi_share_config.git` 同步到 `~/.config/mxbi`，
再将实验仓库同步到 `~/<exp>`，创建 `~/<exp>/data`，并将其加入 cogmoteGO 的
`mxbi-data` source 可信 root。它还部署并启用用户级 `mxbi-experiment.service`，在仓库根目录
执行 `uv run main.py`。部署会停止该服务但保持 enabled，因此需要手动启动；每台设备只有该固定
名称的实验服务。
已有仓库会更新到 `main`；若受 Git 跟踪的文件存在未提交改动，Playbook 会保留这些改动、报告
提示并跳过该仓库的更新。`data/` 等未跟踪文件不会阻止切换。
共享配置仓库采用相同的本地修改保护；若 `~/.config/mxbi` 已存在但不是 Git 仓库，部署会停止，
不会覆盖该目录。
每个实验组通过 `mxbi_experiment_cogmotego_email_recipients` 维护权威订阅者列表；部署时会移除
不属于当前组的地址，并添加缺失地址。
