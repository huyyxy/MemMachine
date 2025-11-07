# 基准评估：测试您的 MemMachine 指南

欢迎使用 MemMachine 评估工具集！我们创建了一个简单的工具，帮助您测量 MemMachine 实例的性能、响应质量，并为您的系统生成 LoCoMo 分数。

**情景记忆工具集：** 该工具测量 MemMachine 执行核心情景记忆任务的速度和准确性。有关具体命令列表，请查看 [情景记忆工具集](./locomo/episodic_memory/README.md)。


## 开始使用

在运行任何基准测试之前，您需要设置环境。

**通用先决条件：**

- **MemMachine 后端：** 所有工具都需要安装并配置 MemMachine 后端。如果您需要帮助，可以查看我们的 [快速入门指南](http://docs.memmachine.ai/getting_started/quickstart)。

- **启动后端：** 一切设置完成后，使用以下命令启动 MemMachine：

  ```sh
  memmachine-server
  ```

**工具特定先决条件：**

- 请确保您的 `cfg.yml` 文件已复制到 `locomo` 目录（`/memmachine/evaluation/locomo/`）并重命名为 `locomo_config.yaml`。


## 运行基准测试

准备好了吗？按照以下简单步骤操作：

**A.** 所有命令都应从其相应的工具目录运行（默认为 `locomo/episodic_memory/`）。

**B.** 您的数据文件 `locomo10.json` 的路径应更新以匹配其位置。默认情况下，您可以在 `/memmachine/evaluation/locomo/` 中找到它。

**C.** 完成下面的步骤 1 后，您可以通过执行步骤 2-4 重复运行基准测试。完成基准测试后，运行步骤 5。

**注意：** 请参考 [情景记忆工具集](./locomo/episodic_memory/README.md) 获取确切命令。

### 步骤 1：导入对话

首先，让我们将对话数据添加到 MemMachine。每次测试运行只需执行一次。

### 步骤 2：搜索对话

让我们搜索您刚刚添加的数据。

### 步骤 3：评估响应

接下来，对搜索结果运行 LoCoMo 评估。

### 步骤 4：生成最终分数

评估完成后，您可以生成最终分数。

输出将是您终端中的一个表格，显示每个类别的平均分数和总体分数，如下例所示：
```sh
Mean Scores Per Category:
          llm_score  count         type
category                               
1            0.8050    282    multi_hop
2            0.7259    321     temporal
3            0.6458     96  open_domain
4            0.9334    841   single_hop

Overall Mean Scores:
llm_score    0.8487
dtype: float64
```

### 步骤 5：清理数据

完成后，您可能想要删除测试数据。
