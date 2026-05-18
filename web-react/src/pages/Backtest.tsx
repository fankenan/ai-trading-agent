import React, { useState } from 'react'
import { Card, Row, Col, Select, Button, Table, Spin, Statistic, Progress, Alert, Tag } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { runBacktest } from '../services/api'

const { Option } = Select

interface BacktestResult {
  total_return: number
  annual_return: number
  max_drawdown: number
  win_rate: number
  profit_loss_ratio: number
  trade_count: number
  sharpe_ratio: number
  trades: TradeRecord[]
}

interface TradeRecord {
  date: string
  action: 'buy' | 'sell'
  price: number
  volume: number
  profit?: number
}

const Backtest: React.FC = () => {
  const [symbol, setSymbol] = useState<string>('000001')
  const [strategy, setStrategy] = useState<string>('trend_following')
  const [days, setDays] = useState<number>(30)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState('')

  const handleRunBacktest = async () => {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await runBacktest(symbol, strategy, days)
      if (response.data.success) {
        const data = response.data.data
        const report = data.report || data
        // Adapt API response to frontend expected format
        setResult({
          total_return: report.total_return || 0,
          annual_return: report.annual_return || 0,
          max_drawdown: report.max_drawdown || 0,
          win_rate: report.win_rate || 0,
          profit_loss_ratio: report.profit_factor || report.profit_loss_ratio || 0,
          trade_count: report.total_trades || report.trade_count || 0,
          sharpe_ratio: report.sharpe_ratio || 0,
          trades: data.trades || [],
        })
      } else {
        setError(response.data.message || '回测失败')
      }
    } catch (err: any) {
      setError('网络错误，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  const tradeColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
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
    },
    {
      title: '盈亏',
      dataIndex: 'profit',
      key: 'profit',
      render: (profit?: number) => {
        if (profit === undefined) return '--'
        return (
          <span style={{ color: profit >= 0 ? '#cf1322' : '#3f8600' }}>
            {profit >= 0 ? '+' : ''}{profit.toFixed(2)}
          </span>
        )
      },
    },
  ]

  return (
    <div>
      <h2>回测系统</h2>

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

      <Card title="回测参数设置" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={8} md={6}>
            <div style={{ marginBottom: 8 }}>选择股票</div>
            <Select
              value={symbol}
              onChange={setSymbol}
              style={{ width: '100%' }}
              placeholder="选择股票"
            >
              <Option value="000001">000001 平安银行</Option>
              <Option value="000002">000002 万科A</Option>
              <Option value="000858">000858 五粮液</Option>
              <Option value="600519">600519 贵州茅台</Option>
              <Option value="300750">300750 宁德时代</Option>
            </Select>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <div style={{ marginBottom: 8 }}>选择策略</div>
            <Select
              value={strategy}
              onChange={setStrategy}
              style={{ width: '100%' }}
              placeholder="选择策略"
            >
              <Option value="trend_following">趋势跟踪策略</Option>
              <Option value="mean_reversion">均值回归策略</Option>
              <Option value="momentum">动量策略</Option>
              <Option value="value">价值投资策略</Option>
              <Option value="breakout">突破策略</Option>
            </Select>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <div style={{ marginBottom: 8 }}>回测天数</div>
            <Select
              value={days}
              onChange={setDays}
              style={{ width: '100%' }}
              placeholder="回测天数"
            >
              <Option value={7}>7天</Option>
              <Option value={30}>30天</Option>
              <Option value={60}>60天</Option>
              <Option value={90}>90天</Option>
              <Option value={180}>180天</Option>
              <Option value={365}>1年</Option>
            </Select>
          </Col>
          <Col xs={24} sm={8} md={6}>
            <div style={{ marginBottom: 8 }}>&nbsp;</div>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleRunBacktest}
              loading={loading}
              disabled={loading}
              size="middle"
            >
              运行回测
            </Button>
          </Col>
        </Row>
      </Card>

      {loading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="正在运行回测，请稍候..." />
          <div style={{ marginTop: 16 }}>
            <Progress percent={50} status="active" showInfo={false} style={{ width: 200 }} />
          </div>
        </Card>
      )}

      {result && !loading && (
        <>
          <Card title="回测结果概览" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="总收益"
                  value={result.total_return}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: result.total_return >= 0 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="年化收益"
                  value={result.annual_return}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: result.annual_return >= 0 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="最大回撤"
                  value={result.max_drawdown}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="胜率"
                  value={result.win_rate}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="盈亏比"
                  value={result.profit_loss_ratio}
                  precision={2}
                />
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="交易次数"
                  value={result.trade_count}
                />
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col xs={24} sm={12}>
                <div style={{ marginBottom: 8 }}>胜率</div>
                <Progress
                  percent={Math.min(result.win_rate, 100)}
                  status={result.win_rate >= 50 ? 'success' : 'exception'}
                  strokeColor={result.win_rate >= 50 ? '#52c41a' : '#ff4d4f'}
                />
              </Col>
              <Col xs={24} sm={12}>
                <div style={{ marginBottom: 8 }}>夏普比率</div>
                <Progress
                  percent={Math.min(Math.max(result.sharpe_ratio * 20, 0), 100)}
                  status={result.sharpe_ratio >= 1 ? 'success' : 'normal'}
                  format={() => result.sharpe_ratio.toFixed(2)}
                />
              </Col>
            </Row>
          </Card>

          <Card title="交易记录">
            <Table
              columns={tradeColumns}
              dataSource={result.trades?.map((trade, index) => ({ ...trade, key: index })) || []}
              pagination={{ pageSize: 10 }}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </>
      )}
    </div>
  )
}

export default Backtest
