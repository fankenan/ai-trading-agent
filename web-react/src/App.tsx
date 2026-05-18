import React, { useState, useEffect, createContext, useContext } from 'react'
import { Layout, Menu, theme, Tag, Select, message } from 'antd'
import {
  DashboardOutlined,
  LineChartOutlined,
  FileTextOutlined,
  StarOutlined,
  WalletOutlined,
  FileDoneOutlined,
  DatabaseOutlined
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import MarketOverview from './pages/MarketOverview'
import Backtest from './pages/Backtest'
import NewsMonitor from './pages/NewsMonitor'
import ScoringDecision from './pages/ScoringDecision'
import PaperTrading from './pages/PaperTrading'
import Reports from './pages/Reports'
import { getDataSource, switchDataSource } from './services/api'

const { Header, Sider, Content } = Layout

type MenuItem = Required<MenuProps>['items'][number]

// 数据源信息
interface SourceInfo {
  key: string
  name: string
  free: boolean
}

export const ALL_SOURCES: Record<string, SourceInfo> = {
  tushare:  { key: 'tushare',  name: 'Tushare Pro', free: true },
  akshare:  { key: 'akshare',  name: 'AKShare',     free: true },
  baostock: { key: 'baostock', name: 'BaoStock',    free: true },
  em:       { key: 'em',       name: '东方财富 EM',  free: true },
  jqdata:   { key: 'jqdata',   name: 'JQData 聚宽',  free: true },
}

export const SOURCE_COLORS: Record<string, string> = {
  tushare: 'blue',
  akshare: 'green',
  baostock: 'orange',
  em: 'red',
  jqdata: 'purple',
}

// 数据源上下文
interface DataSourceContextType {
  currentSource: string
  availableSources: string[]
  setCurrentSource: (source: string) => void
}

export const DataSourceContext = createContext<DataSourceContextType>({
  currentSource: 'tushare',
  availableSources: [],
  setCurrentSource: () => {}
})

export const useDataSource = () => useContext(DataSourceContext)

const items: MenuItem[] = [
  { key: 'market', icon: <DashboardOutlined />, label: '市场概览' },
  { key: 'backtest', icon: <LineChartOutlined />, label: '回测系统' },
  { key: 'news', icon: <FileTextOutlined />, label: '新闻监控' },
  { key: 'scoring', icon: <StarOutlined />, label: '评分决策' },
  { key: 'trading', icon: <WalletOutlined />, label: '模拟交易' },
  { key: 'reports', icon: <FileDoneOutlined />, label: '报告中心' },
]

const App: React.FC = () => {
  const [selectedKey, setSelectedKey] = useState('market')
  const [currentSource, setCurrentSource] = useState('tushare')
  const [availableSources, setAvailableSources] = useState<string[]>([])
  const [switching, setSwitching] = useState(false)
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  // 初始化获取数据源状态
  useEffect(() => {
    fetchDataSource()
  }, [])

  const fetchDataSource = async () => {
    try {
      const res = await getDataSource()
      if (res.data.success && res.data.data) {
        setCurrentSource(res.data.data.current)
        const avail = res.data.data.available || []
        setAvailableSources(avail.map((a: any) => a.key || a))
      }
    } catch (e) {
      console.error('获取数据源状态失败', e)
    }
  }

  const handleSwitchSource = async (newSource: string) => {
    setSwitching(true)
    try {
      const res = await switchDataSource(newSource)
      if (res.data.success) {
        setCurrentSource(newSource)
        message.success(res.data.message || `已切换到 ${newSource}`)
      } else {
        message.error(res.data.message || '切换失败')
      }
    } catch (e: any) {
      message.error('切换数据源失败: ' + (e.message || '未知错误'))
    } finally {
      setSwitching(false)
    }
  }

  const renderContent = () => {
    switch (selectedKey) {
      case 'market':
        return <MarketOverview />
      case 'backtest':
        return <Backtest />
      case 'news':
        return <NewsMonitor />
      case 'scoring':
        return <ScoringDecision />
      case 'trading':
        return <PaperTrading />
      case 'reports':
        return <Reports />
      default:
        return <MarketOverview />
    }
  }

  const sourceInfo = ALL_SOURCES[currentSource] || { name: currentSource, free: false }
  const sourceColor = SOURCE_COLORS[currentSource] || 'default'

  // Build select options for available sources
  const sourceOptions = availableSources.map(key => {
    const info = ALL_SOURCES[key]
    return {
      value: key,
      label: info ? `${info.name}${info.free ? ' (免费)' : ''}` : key,
    }
  })

  return (
    <DataSourceContext.Provider value={{ currentSource, availableSources, setCurrentSource }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#001529' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ color: '#fff', fontSize: 18, fontWeight: 'bold', marginRight: 24 }}>
              ◆ AI量化Agent
            </div>
            <div style={{ color: '#52c41a', fontSize: 14 }}>
              A股市场 · 模拟交易 · 系统运行中
            </div>
          </div>

          {/* 数据源选择器 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <DatabaseOutlined style={{ color: '#fff' }} />
            <Tag color={sourceColor}>{sourceInfo.name}</Tag>
            <Select
              size="small"
              value={currentSource}
              onChange={handleSwitchSource}
              loading={switching}
              style={{ minWidth: 130 }}
              options={sourceOptions}
              placeholder="选择数据源"
            />
          </div>
        </Header>
        <Layout>
          <Sider width={200} style={{ background: colorBgContainer }}>
            <Menu
              mode="inline"
              selectedKeys={[selectedKey]}
              style={{ height: '100%', borderRight: 0 }}
              items={items}
              onClick={({ key }) => setSelectedKey(key)}
            />
          </Sider>
          <Layout style={{ padding: '24px' }}>
            <Content
              style={{
                padding: 24,
                margin: 0,
                minHeight: 280,
                background: colorBgContainer,
                borderRadius: borderRadiusLG,
              }}
            >
              {renderContent()}
            </Content>
          </Layout>
        </Layout>
      </Layout>
    </DataSourceContext.Provider>
  )
}

export default App
