# CHiPmxbi Setup

在控制机上配置和部署 mxbi 实验工作站的工具集。装好后通过 `just` 一键完成设备配置、实验部署与日常更新。

## 安装与初次配置

### 前置条件

- 控制机：macOS / Linux（Ansible 不支持 Windows）。
- 已安装 Homebrew，且能通过 SSH 连接目标机。

> 该仓库只在控制机运行，请勿克隆到目标设备上。

### 安装工具与 collections

```sh
brew install ansible ansible-lint just
```

```sh
ansible-galaxy collection install -r requirements.yml
```

### 首次配置（管理员）

以下文件均已被 Git 忽略，只存在于本机；Vault 文件必须保持加密，禁止以明文写入或提交。

#### 1. Inventory

```sh
cp inventory/hosts.yml.example inventory/hosts.yml
```

默认划分：`group1` = `mxbi[1:5]`，`group2` = `mxbi[6:10]`，另有开发机 `mxbidev`。主机名即 OpenSSH 别名，连接参数由 `~/.ssh/config` 的 `Host mxbi*` 统一提供（`HostName %h.local`、用户 `pi`、`IdentityFile ~/.ssh/mxbi`），inventory 不重复这些信息；inventory 已启用 `StrictHostKeyChecking=accept-new`（首次连接自动记录主机密钥，已记录密钥变化则失败）。

#### 2. GitHub 凭据 Vault（`github` tag 时加载）

```sh
cp vault/mxbi/github.yml.example vault/mxbi/github.yml
ansible-vault encrypt vault/mxbi/github.yml
ansible-vault edit vault/mxbi/github.yml
```

用 `ansible-vault edit` 替换 `vault_github_ssh_private_key` 的占位内容。

#### 3. cogmoteGO email Vault（默认启用）

先确认 `roles/rpi_mxbi_baseline/defaults/main.yml` 中的三个变量（已有默认值）：

- `rpi_mxbi_baseline_cogmotego_email_address`
- `rpi_mxbi_baseline_cogmotego_email_smtp_host`
- `rpi_mxbi_baseline_cogmotego_email_smtp_port`

然后创建并加密密码 Vault：

```sh
cp vault/mxbi/cogmotego_email.yml.example vault/mxbi/cogmotego_email.yml
ansible-vault encrypt vault/mxbi/cogmotego_email.yml
ansible-vault edit vault/mxbi/cogmotego_email.yml
```

将 `vault_cogmotego_email_password` 替换为真实邮件密码。该模块不读取或修改 cogmoteGO recipients（订阅者由实验部署的组变量管理），保存密码前会先准备 login keyring。

#### 4. Samba Vault（可选，`samba` tag 时加载）

```sh
cp vault/mxbi/samba.yml.example vault/mxbi/samba.yml
ansible-vault encrypt vault/mxbi/samba.yml
ansible-vault edit vault/mxbi/samba.yml
```

将 `vault_samba_password` 替换为 `anw-mxbisetup` 的真实密码。

## 常用命令

配置就绪后，日常就两条命令，覆盖绝大部分操作：

### 1. 完整配置设备

```sh
# 全部 mxbi 设备（默认目标）
just baseline-all
# 只配置某一台
just baseline-all mxbi8
```

对 mxbi 设备做一次完整配置：系统软件、HiFiBerry Amp2、Linuxbrew、GitHub SSH 凭据、Zsh、cogmoteGO 及 email、MediaMTX、VNC，并包含默认不执行的 `never` tag（Samba）。需要 Vault 密码；幂等，可重复运行；只想查看将做的改动用 `just baseline-check mxbi1`。

### 2. 部署实验

```sh
# 全部设备
just exp mxbi
# 只部署某一台
just exp mxbi8
```

按组变量把实验部署到设备。设备需先完成 baseline；预览改动用 `just exp-check mxbi1`。

`experiment.yml` 是实验部署入口，假定 Samba、GitHub SSH、cogmoteGO 与 uv 已就绪，不会重新配置这些组件。实验组位于 inventory 的 `mxbi_experiments` 之下，组名与实验名相互独立；每个实验组对应一个组变量文件，例如 `group_vars/group1.yml`：

```yaml
mxbi_experiment_name: <实验名>
mxbi_experiment_repository: git@github.com:<组织>/<实验仓库>.git
mxbi_experiment_uv_sync: true
mxbi_experiment_cogmotego_email_recipients:
  - <订阅者邮箱>
```

## 其他命令

### 按需操作（tags）

只做部分配置时，用 `--tags` 指定（会透传给 Ansible）。最常用的是 `update`：只升级 APT 与 Homebrew 包，不加载任何 Vault，仅提示 sudo 密码：

```sh
just baseline mxbi1 --tags update
```

其他常用示例：

```sh
just baseline mxbi1 --tags shell
just baseline mxbi1 --tags 'system,homebrew'
just baseline mxbi1 --tags github
just baseline mxbi5 --tags cogmotego_email
just baseline mxbi5 --tags samba
```

| tag               | 作用                                                                                                                                                                                                                                            |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `system`          | 系统软件包                                                                                                                                                                                                                                      |
| `hifiberry`       | HiFiBerry Amp2 配置                                                                                                                                                                                                                             |
| `homebrew`        | Linuxbrew 与托管 formula                                                                                                                                                                                                                        |
| `github`          | GitHub SSH 凭据（加载 GitHub Vault）                                                                                                                                                                                                            |
| `shell`           | Zsh 配置                                                                                                                                                                                                                                        |
| `cogmotego`       | cogmoteGO                                                                                                                                                                                                                                       |
| `cogmotego_email` | cogmoteGO email（加载 email Vault）                                                                                                                                                                                                             |
| `mediamtx`        | MediaMTX                                                                                                                                                                                                                                        |
| `desktop`         | 桌面与 VNC                                                                                                                                                                                                                                      |
| `samba`           | Samba 挂载（`never` tag，默认不执行；加载 Samba Vault，将 `//infortrend-storage/Neurowissenschaften/AuditorischeNeurowissenschaften/Projekte/MXBI/data/<主机名>` 挂载到 `/home/pi/server`，注册 `mxbi-server` 可信根并重启 cogmoteGO 用户服务） |
| `update`          | 仅 APT 缓存刷新与安全升级 + Homebrew formula 升级（不加载任何 Vault）                                                                                                                                                                           |

平台校验与用户变量初始化使用 `always` tag，任何选择性执行都会先运行它们。

### 全部命令

`just` 命令的参数会直接传给 Ansible。读取 Vault 的配方会提示输入 Vault 密码；`just update` 不读取任何 Vault，因此只提示 sudo 密码。

| 命令                            | 作用                                 | 需要 Vault 密码 |
| ------------------------------- | ------------------------------------ | --------------- |
| `just install`                  | 安装 Ansible collections             | 否              |
| `just check`                    | lint + 两个 playbook 语法检查        | 否              |
| `just inventory`                | 显示 inventory 分组与主机            | 否              |
| `just tags`                     | 列出 baseline playbook 的 tags       | 否              |
| `just baseline [主机/组]`       | 完整配置设备（默认全部 mxbi）        | 是              |
| `just baseline-all [主机/组]`   | 完整配置，含 `never` tag（如 samba） | 是              |
| `just baseline-check <主机/组>` | 配置检查模式（`--check --diff`）     | 是              |
| `just exp <主机/组>`            | 部署实验                             | 否              |
| `just exp-check <主机/组>`      | 实验部署检查模式                     | 否              |
| `just samba <主机/组>`          | 挂载 Samba                           | 是              |
| `just update [主机/组]`         | 仅升级 APT 与 Homebrew 包            | 仅 sudo         |

## 常见问题

- **提示输入 Vault 密码**：Vault 密码由团队管理员保管，需要时向管理员获取。
- **连不上设备**：先 `ssh -G mxbi1` 检查解析结果（HostName / User / IdentityFile），确认 `~/.ssh/mxbi` 密钥存在且已注册到设备。
- **报 collections 缺失**：重新执行 `just install`。
