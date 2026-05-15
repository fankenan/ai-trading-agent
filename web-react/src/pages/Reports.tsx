import React, { useState } from 'react'
import { Card, Button, DatePicker, Select, Divider, Typography, Spin, Alert, Row, Col, Tag, Table, Statistic } from 'antd'
import { FileTextOutlined, DownloadOutlined, CalendarOutlined, BarChartOutlined, LineChartOutlined, PieChartOutlined } from '@ant-design/icons'
import { getReport } from '../services/api'
import type { Dayjs } from 'dayjs'

const { Text, Title, Paragraph } = Typography
const { Option } = Select
const { RangePicker } = DatePicker

interface ReportData {
  type: string
  generated_at: string
  period: {
    start: string
    end: string
  }
  summary: string
  metrics: {
    total_return: number
    annual_return: number
    max_drawdown: number
    sharpe_ratio: number
    trade_count: number
    win_rate: number
  }
  holdings: Array<{
    symbol: string
    name: string
    weight: number
    return: number
  }>
  trades: Array<{
    date: string
    symbol: string
    action: string
    price: number
    volume: number
  }>
  content?: string
}

const Reports: React.FC = () => {
  const [reportType, setReportType] = useState<string>('daily')
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [singleDate, setSingleDate] = useState<Dayjs | null>(null)
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<ReportData | null>(null)
  const [error, setError] = useState('')

  const handleGenerateReport = async () => {
    setLoading(true)
    setError('')
    setReport(null)

    try {
      const params: any = { type: reportType }

      if (reportType === 'custom' && dateRange && dateRange[0] && dateRange[1]) {
        params.start_date = dateRange[0].format('YYYY-MM-DD')
        params.end_date = dateRange[1].format('YYYY-MM-DD')
      } else if (singleDate) {
        params.date = singleDate.format('YYYY-MM-DD')
      }

      const response = await getReport(params)
      if (response.data.success) {
        setReport(response.data.data)
      } else {
        setError(response.data.message || '生成报告失败')
      }
    } catch (err: any) {
      setError('网络错误，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  const handleExportReport = () => {
    if (!report) return

    const reportContent = JSON.stringify(report, null, 2)
    const blob = new Blob([reportContent], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `report_${report.type}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const getReportTypeIcon = (type: string) => {
    switch (type) {
      case 'daily':
        return <CalendarOutlined />
      case 'weekly':
        return <BarChartOutlined />
      case 'monthly':
        return <LineChartOutlined />
      case 'quarterly':
        return <PieChartOutlined />
      default:
        return <FileTextOutlined />
    }
  }

  const getReportTypeText = (type: string) => {
    switch (type) {
      case 'daily':
        return '日报'
      case 'weekly':
        return '周报'
      case 'monthly':
        return '月报'
      case 'quarterly':
        return '季报'
      case 'custom':
        return '自定义报告'
      default:
        return type
    }
  }

  const holdingColumns = [
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
      title: '权重',
      dataIndex: 'weight',
      key: 'weight',
      render: (weight: number) => `${weight.toFixed(2)}%`,
    },
    {
      title: '收益',
      dataIndex: 'return',
      key: 'return',
      render: (ret: number) => (
        <span style={{ color: ret >= 0 ? '#cf1322' : '#3f8600' }}>
          {ret >= 0 ? '+' : ''}{ret.toFixed(2)}%
        </span>
      ),
    },
  ]

  const tradeColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
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
  ]

  return (
    <div>
      <h2>报告中心</h2>

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

      <Card title="报告生成设置" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={12} md={6}>
            <div style={{ marginBottom: 8 }}>报告类型</div>
            <Select
              value={reportType}
              onChange={setReportType}
              style={{ width: '100%' }}
              placeholder="选择报告类型"
            >
              <Option value="daily">日报</Option>
              <Option value="weekly">周报</Option>
              <Option value="monthly">月报</Option>
              <Option value="quarterly">季报</Option>
              <Option value="custom">自定义</Option>
            </Select>
          </Col>

          {reportType === 'custom' ? (
            <Col xs={24} sm={12} md={8}>
              <div style={{ marginBottom: 8 }}>日期范围</div>
              <RangePicker
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [Dayjs | null, Dayjs | null])}
                style={{ width: '100%' }}
                placeholder={['开始日期', '结束日期']}
              />
            </Col>
          ) : (
            <Col xs={24} sm={12} md={6}>
              <div style={{ marginBottom: 8 }}>选择日期</div>
              <DatePicker
                value={singleDate}
                onChange={setSingleDate}
                style={{ width: '100%' }}
                placeholder="选择日期"
              />
            </Col>
          )}

          <Col xs={24} sm={12} md={reportType === 'custom' ? 4 : 6}>
            <div style={{ marginBottom: 8 }}>&nbsp;</div>
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              onClick={handleGenerateReport}
              loading={loading}
              disabled={loading || (reportType === 'custom' ? !dateRange || !dateRange[0] || !dateRange[1] : !singleDate)}
            >
              生成报告
            </Button>
          </Col>
        </Row>
      </Card>

      {loading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="正在生成报告..." />
        </Card>
      )}

      {report && !loading && (
        <Card
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                {getReportTypeIcon(report.type)}
                <span style={{ marginLeft: 8 }}>
                  {getReportTypeText(report.type)} - {report.period?.start} 至 {report.period?.end}
                </span>
              </div>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportReport}
                size="small"
              >
                导出JSON
              </Button>
            </div>
          }
        >
          {/* 报告摘要 */}
          <div style={{ marginBottom: 24 }}>
            <Title level={4}>报告摘要</Title>
            <Paragraph>{report.summary}</Paragraph>
            <Text type="secondary">
              生成时间: {new Date(report.generated_at).toLocaleString()}
            </Text>
          </div>

          <Divider />

          {/* 关键指标 */}
          <div style={{ marginBottom: 24 }}>
            <Title level={4}>关键指标</Title>
            <Row gutter={16}>
              <Col xs={12} sm={8} md={4}>
                <Card size="small">
                  <Statistic
                    title="总收益"
                    value={report.metrics?.total_return || 0}
                    precision={2}
                    suffix="%"
                    valueStyle={{ color: (report.metrics?.total_return || 0) >= 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small">
                  <Statistic
                    title="年化收益"
                    value={report.metrics?.annual_return || 0}
                    precision={2}
                    suffix="%"
                    valueStyle={{ color: (report.metrics?.annual_return || 0) >= 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small">
                  <Statistic
                    title="最大回撤"
                    value={report.metrics?.max_drawdown || 0}
                    precision={2}
                    suffix="%"
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small">
                  <Statistic
                    title="夏普比率"
                    value={report.metrics?.sharpe_ratio || 0}
                    precision={2}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small">
                  <Statistic
                    title="交易次数"
                    value={report.metrics?.trade_count || 0}
                  />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small">
                  <Statistic
                    title="胜率"
                    value={report.metrics?.win_rate || 0}
                    precision={2}
                    suffix="%"
                  />
                </Card>
              </Col>
            </Row>
          </div>

          <Divider />

          {/* 持仓分布 */}
          {report.holdings && report.holdings.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <Title level={4}>持仓分布</Title>
              <Table
                columns={holdingColumns}
                dataSource={report.holdings.map((h, index) => ({ ...h, key: index }))}
                pagination={false}
                size="small"
              />
            </div>
          )}

          <Divider />

          {/* 交易记录 */}
          {report.trades && report.trades.length > 0 && (
            <div>
              <Title level={4}>交易记录</Title>
              <Table
                columns={tradeColumns}
                dataSource={report.trades.map((t, index) => ({ ...t, key: index }))}
                pagination={{ pageSize: 10 }}
                size="small"
              />
            </div>
          )}

          {/* 原始内容 */}
          {report.content && (
            <>
              <Divider />
              <div>
                <Title level={4}>详细内容</Title>
                <div
                  style={{
                    backgroundColor: '#f6f8fa',
                    padding: 16,
                    borderRadius: 6,
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {report.content}
                </div>
              </div>
            </>
          )}
        </Card>
      )}

      {!report && !loading && (
        <Card style={{ textAlign: 'center', padding: 60 }}>
          <FileTextOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
          <p style={{ marginTop: 16, color: '#999' }}>请选择报告类型和日期，然后点击生成报告</p>
        </Card>
      )}
    </div>
  )
}

export default Reports
