import React, { useState, useEffect } from 'react'
import { Card, Table, Statistic, Row, Col, Empty, Spin, Alert, Tag, Badge, Typography, Timeline } from 'antd'
import { WalletOutlined, FundOutlined, DollarOutlined, RiseOutlined, FallOutlined, ReloadOutlined, HistoryOutlined, ShoppingOutlined } from '@ant-design/icons'
import { getStatus } from '../services/api'

const { Text } = Typography

interface Position {
  symbol: string
  name: string
  volume: number
  avg_price: number
  current_price: number
  market_value: number
  profit_loss: number
  profit_loss_pct: number
  weight: number
}

interface Trade {
  id: string
  time: string
  symbol: string
  action: 'buy' | 'sell'
  price: number
  volume: number
  amount: number
  profit_loss?: number
}

interface EquityData {
  date: string
  total_equity: number
  cash: number
  market_value: number
}

interface PortfolioStatus {
  balance: number
  total_equity: number
  market_value: number
  available_cash: number
  daily_pnl: number
  daily_pnl_pct: number
  total_return: number
  total_return_pct: number
  positions: Position[]
  trades: Trade[]
  equity_curve: EquityData[]
}

const PaperTrading: React.FC = () => {
  const [status, setStatus] = useState<PortfolioStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchStatus = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await getStatus()
      if (response.data.success) {
        setStatus(response.data.data)
      } else {
        setError(response.data.message || '获取交易状态失败')
      }
    } catch (err: any) {
      setError('网络错误，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  // 自动刷新（每30秒更新）
  useEffect(() => {
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const positionColumns = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '股票名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '持仓数量',
      dataIndex: 'volume',
      key: 'volume',
      render: (volume: number) => volume.toLocaleString(),
    },
    {
      title: '成本价',
      dataIndex: 'avg_price',
      key: 'avg_price',
      render: (price: number) => `¥${price.toFixed(2)}`,
    },
    {
      title: '现价',
      dataIndex: 'current_price',
      key: 'current_price',
      render: (price: number) => `¥${price.toFixed(2)}`,
    },
    {
      title: '市值',
      dataIndex: 'market_value',
      key: 'market_value',
      render: (value: number) => `¥${value.toLocaleString()}`,
    },
    {
      title: '盈亏',
      dataIndex: 'profit_loss',
      key: 'profit_loss',
      render: (pl: number, record: Position) => (
        <div>
          <span style={{ color: pl >= 0 ? '#cf1322' : '#3f8600' }}>
            {pl >= 0 ? '+' : ''}{pl.toLocaleString()}
          </span>
          <br />
          <Text type="secondary" style={{ fontSize: 12, color: pl >= 0 ? '#cf1322' : '#3f8600' }}>
            ({record.profit_loss_pct >= 0 ? '+' : ''}{record.profit_loss_pct.toFixed(2)}%)
          </Text>
        </div>
      ),
    },
    {
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      render: (weight: number) => `${weight.toFixed(2)}%`,
    },
  ]

  const tradeColumns = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '股票',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => (
        <Tag color={action === 'buy' ? 'green' : 'red'}>
          {action === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => `¥${price.toFixed(2)}`,
    },
    {
      title: '数量',
      dataIndex: 'volume',
      key: 'volume',
      render: (volume: number) => volume.toLocaleString(),
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `¥${amount.toLocaleString()}`,
    },
    {
      title: '盈亏',
      dataIndex: 'profit_loss',
      key: 'profit_loss',
      render: (pl?: number) => {
        if (pl === undefined) return '--'
        return (
          <span style={{ color: pl >= 0 ? '#cf1322' : '#3f8600' }}>
            {pl >= 0 ? '+' : ''}{pl.toLocaleString()}
          </span>
        )
      },
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>模拟交易</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Badge status="processing" text="实时更新" style={{ marginRight: 8 }} />
          <Tag icon={<ReloadOutlined />} color="blue" onClick={fetchStatus} style={{ cursor: 'pointer' }}>
            刷新
          </Tag>
        </div>
      </div>

      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setError('')}
        />
      )}

      {loading && !status ? (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="加载中..." />
        </Card>
      ) : status ? (
        <>
          {/* 资产概览 */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="总资产"
                  value={status.total_equity}
                  precision={2}
                  prefix={<WalletOutlined />}
                  formatter={(value) => `¥${Number(value).toLocaleString()}`}
                />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    总收益率:
                    <span style={{ color: status.total_return_pct >= 0 ? '#cf1322' : '#3f8600' }}>
                      {status.total_return_pct >= 0 ? '+' : ''}{status.total_return_pct.toFixed(2)}%
                    </span>
                  </Text>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="持仓市值"
                  value={status.market_value}
                  precision={2}
                  prefix={<FundOutlined />}
                  formatter={(value) => `¥${Number(value).toLocaleString()}`}
                />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">
                    仓位: {((status.market_value / status.total_equity) * 100).toFixed(2)}%
                  </Text>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="可用资金"
                  value={status.available_cash}
                  precision={2}
                  prefix={<DollarOutlined />}
                  formatter={(value) => `¥${Number(value).toLocaleString()}`}
                />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">可用于交易</Text>
                </div>
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="今日盈亏"
                  value={status.daily_pnl}
                  precision={2}
                  prefix={status.daily_pnl >= 0 ? <RiseOutlined /> : <FallOutlined />}
                  valueStyle={{ color: status.daily_pnl >= 0 ? '#cf1322' : '#3f8600' }}
                  formatter={(value) => `${Number(value) >= 0 ? '+' : ''}¥${Number(value).toLocaleString()}`}
                />
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ color: status.daily_pnl_pct >= 0 ? '#cf1322' : '#3f8600' }}>
                    {status.daily_pnl_pct >= 0 ? '+' : ''}{status.daily_pnl_pct.toFixed(2)}%
                  </Text>
                </div>
              </Card>
            </Col>
          </Row>

          {/* 持仓和交易 */}
          <Row gutter={16}>
            <Col xs={24} lg={14} style={{ marginBottom: 16 }}>
              <Card
                title={
                  <div>
                    <ShoppingOutlined style={{ marginRight: 8 }} />
                    当前持仓
                    <Badge
                      count={status.positions?.length || 0}
                      style={{ backgroundColor: '#1890ff', marginLeft: 8 }}
                    />
                  </div>
                }
              >
                {status.positions && status.positions.length > 0 ? (
                  <Table
                    columns={positionColumns}
                    dataSource={status.positions.map((pos, index) => ({ ...pos, key: index }))}
                    pagination={false}
                    size="small"
                    scroll={{ x: 'max-content' }}
                  />
                ) : (
                  <Empty description="暂无持仓" />
                )}
              </Card>
            </Col>

            <Col xs={24} lg={10} style={{ marginBottom: 16 }}>
              <Card
                title={
                  <div>
                    <HistoryOutlined style={{ marginRight: 8 }} />
                    交易历史
                  </div>
                }
              >
                {status.trades && status.trades.length > 0 ? (
                  <Timeline mode="left">
                    {status.trades.slice(0, 5).map((trade) => (
                      <Timeline.Item
                        key={trade.id}
                        color={trade.action === 'buy' ? 'green' : 'red'}
                        label={new Date(trade.time).toLocaleDateString()}
                      >
                        <div>
                          <Tag color={trade.action === 'buy' ? 'green' : 'red'}>
                            {trade.action === 'buy' ? '买入' : '卖出'}
                          </Tag>
                          <Text strong> {trade.symbol}</Text>
                          <br />
                          <Text type="secondary">
                            {trade.volume.toLocaleString()}股 @ ¥{trade.price.toFixed(2)}
                          </Text>
                          {trade.profit_loss !== undefined && (
                            <div style={{ color: trade.profit_loss >= 0 ? '#cf1322' : '#3f8600' }}>
                              盈亏: {trade.profit_loss >= 0 ? '+' : ''}{trade.profit_loss.toLocaleString()}
                            </div>
                          )}
                        </div>
                      </Timeline.Item>
                    ))}
                  </Timeline>
                ) : (
                  <Empty description="暂无交易记录" />
                )}
              </Card>
            </Col>
          </Row>

          {/* 完整交易记录表 */}
          <Card
            title="完整交易记录"
            style={{ marginBottom: 16 }}
          >
            {status.trades && status.trades.length > 0 ? (
              <Table
                columns={tradeColumns}
                dataSource={status.trades.map((trade) => ({ ...trade, key: trade.id }))}
                pagination={{ pageSize: 10 }}
                size="small"
                scroll={{ x: 'max-content' }}
              />
            ) : (
              <Empty description="暂无交易记录" />
            )}
          </Card>
        </>
      ) : (
        <Card style={{ textAlign: 'center', padding: 60 }}>
          <Empty description="暂无数据" />
        </Card>
      )}
    </div>
  )
}

export default PaperTrading
