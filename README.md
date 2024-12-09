## volpro 纯脚本版本 

做了简单的优化

## 安装依赖

```bash
pip install tqdm
```

## 基本用法

1. 基本分析：
```bash
python volpro.py <内存镜像路径>
```

2. 指定 Profile：
```bash
python volpro.py <内存镜像路径> --profile Win7SP1x64
```

3. 导出特定文件：
```bash
python volpro.py <内存镜像路径> --profile Win7SP1x64 --dumpfiles --dumpfiles-location 0x12345678
```

## 参数说明

- `memorydump_path`：必需，内存镜像文件的路径
- `--profile`：可选，指定 Volatility Profile，如不指定将自动检测
- `--dumpfiles`：可选，启用文件导出功能
- `--dumpfiles-location`：可选，要导出的文件内存位置
- `--timeout`：可选，单个任务超时时间（秒），默认 120 秒
- `--volatility-path`：可选，Volatility 程序路径，默认为 'vol.exe'

