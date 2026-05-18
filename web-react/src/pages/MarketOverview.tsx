import React, { useState, useEffect, useContext } from 'react'
import { Card, Row, Col, Statistic, Select, Button, Table, Alert, Tag, Divider, Spin } from 'antd'
import { ReloadOutlined, RiseOutlined, FallOutlined, DatabaseOutlined } from '@ant-design/icons'
import { DataSourceContext, ALL_SOURCES, SOURCE_COLORS } from '../App'

const STOCK_LIST = [
  { value: '000001', label: '000001 平安银行' },
  { value: '000002', label: '000002 万科A' },
  { value: '000858', label: '000858 五粮液' },
  { value: '600519', label: '600519 贵州茅台' },
  { value: '300750', label: '300750 宁德时代' },
]

const MarketOverview: React.FC = () => {
  const { currentSource } = useContext(DataSourceContext)
  const [symbol, setSymbol] = useState('000001')
  const [loading, setLoading] = useState(false)
  const [quote, setQuote] = useState<any>(null)
  const [status, setStatus] = useState<any>(null)
  const [error, setError] = useState('')

  const sourceName = ALL_SOURCES[currentSource]?.name || currentSource
  const sourceColor = SOURCE_COLORS[currentSource] || 'default'

  const fetchData = async () => {
    setLoading(true)
    setError('')
    
    try {
      // 获取系统状态
      const statusRes = await fetch('/api/status')
      const statusData = await statusRes.json()
      if (statusData.success) {
        setStatus(statusData.data)
      }

      // 获取行情数据
      const marketRes = await fetch(`/api/market?symbol=${symbol}&days=30`)
      const marketData = await marketRes.json()
      
      if (marketData.success && marketData.data?.quote) {
        setQuote(marketData.data.quote)
      } else {
        setError(marketData.message || '获取数据失败')
        setQuote(null)
      }
    } catch (err: any) {
      setError('网络错误: ' + err.message)
      setQuote(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [symbol])

  const columns = [
    { title: '指标', dataIndex: 'label', key: 'label' },
    { title: '数值', dataIndex: 'value', key: 'value' },
  ]

  const data = quote ? [
    { key: '1', label: '股票代码', value: quote.symbol },
    { key: '2', label: '股票名称', value: quote.name },
    { key: '3', label: '今开', value: `¥${quote.open?.toFixed(2)}` },
    { key: '4', label: '最高', value: `¥${quote.high?.toFixed(2)}` },
    { key: '5', label: '最低', value: `¥${quote.low?.toFixed(2)}` },
    { key: '6', label: '昨收', value: `¥${quote.pre_close?.toFixed(2)}` },
    { key: '7', label: '成交量', value: `${(quote.volume / 10000).toFixed(2)}万手` },
    { key: '8', label: '成交额', value: `${(quote.amount / 100000000).toFixed(2)}亿` },
    { key: '9', label: '换手率', value: `${quote.turnover?.toFixed(2)}%` },
    { key: '10', label: '市盈率(动态)', value: quote.pe?.toFixed(2) || '--' },
    { key: '11', label: '市净率', value: quote.pb?.toFixed(2) || '--' },
  ] : []

  return (
    <div>
      <h2>市场概览</h2>
      
      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" type="primary" onClick={fetchData}>
              重试
            </Button>
          }
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Select
            value={symbol}
            onChange={setSymbol}
            style={{ width: '100%' }}
            options={STOCK_LIST}
          />
        </Col>
        <Col span={8}>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={fetchData}
            loading={loading}
          >
            刷新数据
          </Button>
        </Col>
        <Col span={8}>
          <Tag color={sourceColor} icon={<DatabaseOutlined />}>
            {sourceName}
          </Tag>
        </Col>
      </Row>

      {loading && !quote && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="加载中..." />
        </div>
      )}

      {quote && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="当前价格"
                  value={quote.price}
                  precision={2}
                  prefix="¥"
                  valueStyle={{
                    color: quote.change_pct >= 0 ? '#cf1322' : '#3f8600'
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="涨跌幅"
                  value={quote.change_pct}
                  precision={2}
                  suffix="%"
                  prefix={quote.change_pct >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  valueStyle={{
                    color: quote.change_pct >= 0 ? '#cf1322' : '#3f8600'
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="涨跌额"
                  value={quote.change}
                  precision={2}
                  prefix={quote.change >= 0 ? '+' : ''}
                  valueStyle={{
                    color: quote.change >= 0 ? '#cf1322' : '#3f8600'
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="总市值"
                  value={quote.market_cap ? (quote.market_cap / 100000000).toFixed(2) : '--'}
                  suffix="亿"
                />
              </Card>
            </Col>
          </Row>

          <Divider />

          <Row gutter={16}>
            <Col span={12}>
              <Card title="股票详情">
                <Table
                  columns={columns}
                  dataSource={data}
                  pagination={false}
                  size="small"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="系统状态">
                {status ? (
                  <div>
                    <p><strong>市场类型:</strong> <Tag color="blue">{status.market}</Tag></p>
                    <p><strong>数据源:</strong> <Tag color="green">{status.data_source}</Tag></p>
                    <p><strong>运行模式:</strong> <Tag color={status.mode === 'paper' ? 'green' : 'red'}>{status.mode === 'paper' ? '模拟交易' : '实盘'}</Tag></p>
                    <p><strong>初始资金:</strong> ¥{status.portfolio?.balance?.toLocaleString()}</p>
                    <p><strong>当前权益:</strong> ¥{status.portfolio?.total_equity?.toLocaleString()}</p>
                    <p><strong>最后更新:</strong> {new Date(status.timestamp).toLocaleString()}</p>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', color: '#999' }}>加载中...</div>
                )}
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  )
}

export default MarketOverview
