import type { FullConfig } from '@nekosu/maa-tools'

const config: FullConfig = {
  cwd: import.meta.dirname,
  maaVersion: 'latest',
  interfacePath: 'assets/interface.json',
  check: {
    override: {
      'unknown-task': 'ignore',
      // maafw 允许同一节点同时出现在 next 和 on_error 里（超时后先复查再重试）
      'duplicate-next': 'ignore'
    }
  }
}

export default config
