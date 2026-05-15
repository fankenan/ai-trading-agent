import React, { useState, useEffect } from 'react'
import { Card, Input, Button, List, Tag, Empty, Alert, message, Row, Col, Typography } from 'antd'
import { SendOutlined, FileTextOutlined } from '@ant-design/icons'

const { TextArea } = Input
const { Text } = Typography

const NewsMonitor: React.FC = () => {
  const [newsList, setNewsList] = useState<any[]>([])
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [source] = useState('用户提交')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 初始加载新闻数据
  useEffect(() => {
    fetchNews()
  }, [])

  const fetchNews = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/news')
      const data = await res.json()
      if (data.success && data.data?.news) {
        setNewsList(data.data.news)
      } else {
        setNewsList([])
      }
    } catch (err) {
      setError('获取新闻数据失败，请检查后端服务是否正常运行')
      setNewsList([])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!title.trim()) {
      message.warning('请输入新闻标题')
      return
    }
    
    const newNews = {
      id: Date.now().toString(),
      title,
      content: content || '无详细内容',
      source,
      is_policy: title.includes('政策') || title.includes('央行') || title.includes('证监会'),
      sentiment: 'neutral',
      publish_time: new Date().toISOString()
    }
    
    setNewsList([newNews, ...newsList])
    message.success('新闻已提交！')
    setTitle('')
    setContent('')
  }

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case 'positive': return 'green'
      case 'negative': return 'red'
      default: return 'default'
    }
  }

  const getSentimentText = (sentiment?: string) => {
    switch (sentiment) {
      case 'positive': return '利好'
      case 'negative': return '利空'
      default: return '中性'
    }
  }

  return (
    <div>
      <h2>新闻监控</h2>
      
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
      
      <Card title="提交新闻事件" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={24}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>新闻标题</Text>
            <Input 
              placeholder="请输入新闻标题" 
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ marginBottom: 16 }}
            />
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={24}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>新闻内容</Text>
            <TextArea 
              placeholder="请输入新闻内容" 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={3}
              style={{ marginBottom: 16 }}
            />
          </Col>
        </Row>
        <Button type="primary" icon={<SendOutlined />} onClick={handleSubmit}>
          提交新闻
        </Button>
      </Card>

      <Card 
        title={`事件列表 (${newsList.length}条)`}
        extra={<Button onClick={fetchNews} loading={loading}>刷新</Button>}
      >
        {newsList.length === 0 ? (
          <Empty description="暂无新闻数据" />
        ) : (
          <List
            dataSource={newsList}
            renderItem={(item) => (
              <List.Item style={{ background: item.is_policy ? '#fff7e6' : 'transparent', padding: 16, borderRadius: 8, marginBottom: 8 }}>
                <List.Item.Meta
                  title={
                    <span>
                      <FileTextOutlined style={{ marginRight: 8 }} />
                      {item.title}
                      {item.is_policy && <Tag color="orange" style={{ marginLeft: 8 }}>政策相关</Tag>}
                      <Tag color={getSentimentColor(item.sentiment)} style={{ marginLeft: 8 }}>{getSentimentText(item.sentiment)}</Tag>
                    </span>
                  }
                  description={
                    <div>
                      <Text type="secondary">来源: {item.source} | 时间: {new Date(item.publish_time).toLocaleString()}</Text>
                      <br />
                      <Text>{item.content}</Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}

export default NewsMonitor
