import React, { useState, useEffect, createContext, useContext } from 'react'
import { Layout, Menu, theme, Tag, Button, Tooltip, message } from 'antd'
import {
  DashboardOutlined,
  LineChartOutlined,
  FileTextOutlined,
  StarOutlined,
  WalletOutlined,
  FileDoneOutlined,
  DatabaseOutlined,
  SwapOutlined
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

// 数据源上下文
interface DataSourceContextType {
  currentSource: 'akshare' | 'tushare'
  setCurrentSource: (source: 'akshare' | 'tushare') => void
}

export const DataSourceContext = createContext<DataSourceContextType>({
  currentSource: 'akshare',
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
  const [currentSource, setCurrentSource] = useState<'akshare' | 'tushare'>('akshare')
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
      if (res.data.success && res.data.data?.current) {
        setCurrentSource(res.data.data.current)
      }
    } catch (e) {
      console.error('获取数据源状态失败', e)
    }
  }

  const handleSwitchSource = async () => {
    const newSource = currentSource === 'akshare' ? 'tushare' : 'akshare'
    setSwitching(true)
    try {
      const res = await switchDataSource(newSource)
      if (res.data.success) {
        setCurrentSource(newSource)
        message.success(`已切换到 ${newSource.toUpperCase()} 数据源`)
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

  return (
    <DataSourceContext.Provider value={{ currentSource, setCurrentSource }}>
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
          
          {/* 数据源切换按钮 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <DatabaseOutlined style={{ color: '#fff' }} />
            <Tag color={currentSource === 'akshare' ? 'green' : 'blue'}>
              {currentSource === 'akshare' ? 'AKShare' : 'Tushare'}
            </Tag>
            <Tooltip title={`切换到 ${currentSource === 'akshare' ? 'Tushare' : 'AKShare'} 数据源`}>
              <Button 
                type="primary" 
                size="small"
                icon={<SwapOutlined />}
                loading={switching}
                onClick={handleSwitchSource}
                style={{ background: currentSource === 'akshare' ? '#1890ff' : '#52c41a', borderColor: 'transparent' }}
              >
                切换
              </Button>
            </Tooltip>
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
