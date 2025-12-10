import React, { useState } from 'react';
import { Layout, Tabs, Card, Form, Input, Button, Upload, message } from 'antd';
import { UploadOutlined, SearchOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Header, Content, Footer } = Layout;

const App = () => {
  const [loading, setLoading] = useState(false);
  const [singleResult, setSingleResult] = useState(null);
  const [activeTab, setActiveTab] = useState('1');

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  // Single Geocode
  const onFinishGeo = async (values) => {
    setLoading(true);
    try {
      const res = await axios.post('/api/geo', values);
      if (res.data.status === 'success') {
        setSingleResult(res.data.data);
        message.success('查询成功');
      } else {
        message.error('未找到相关地址信息');
      }
    } catch (error) {
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  // Single Regeocode
  const onFinishRegeo = async (values) => {
    setLoading(true);
    try {
      const res = await axios.post('/api/regeo', values);
      if (res.data.status === 'success') {
        setSingleResult(res.data.data);
        message.success('查询成功');
      } else {
        message.error('未找到相关位置信息');
      }
    } catch (error) {
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  // Batch Upload
  const uploadProps = (type) => ({
    name: 'file',
    customRequest: async ({ file, onSuccess, onError }) => {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await axios.post(`/api/batch/file/${type}`, formData, {
          responseType: 'blob',
        });
        downloadBlob(new Blob([res.data]), `processed_${file.name}.xlsx`);
        message.success(`${file.name} 处理成功`);
        onSuccess({}, file);
      } catch (err) {
        message.error(`${file.name} 处理失败`);
        onError(err);
      }
    }
  });

  const GeoTab = () => (
    <div className="space-y-6">
      <Card title="单条查询" variant="borderless">
        <Form layout="inline" onFinish={onFinishGeo}>
          <Form.Item name="address" rules={[{ required: true, message: '请输入地址' }]}>
            <Input placeholder="请输入详细地址" style={{ width: 300 }} />
          </Form.Item>
          <Form.Item name="city">
            <Input placeholder="城市 (可选)" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
              查询
            </Button>
          </Form.Item>
        </Form>
        {singleResult && singleResult.location && (
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <p><strong>经纬度:</strong> {singleResult.location}</p>
            <p><strong>格式化地址:</strong> {singleResult.formatted_address}</p>
            <p><strong>行政区:</strong> {singleResult.province} {singleResult.city} {singleResult.district}</p>
          </div>
        )}
      </Card>

      <Card title="批量处理 (Excel/CSV)" variant="borderless">
        <p className="mb-4 text-gray-500">请上传包含"地址"列的 Excel 或 CSV 文件。</p>
        <Upload {...uploadProps('geo')}>
          <Button icon={<UploadOutlined />}>上传文件并处理</Button>
        </Upload>
      </Card>
    </div>
  );

  const RegeoTab = () => (
    <div className="space-y-6">
      <Card title="单条查询" variant="borderless">
        <Form layout="inline" onFinish={onFinishRegeo}>
          <Form.Item name="location" rules={[{ required: true, message: '请输入经纬度' }]}>
            <Input placeholder="经度,纬度 (如: 116.48,39.99)" style={{ width: 300 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
              查询
            </Button>
          </Form.Item>
        </Form>
        {singleResult && singleResult.formatted_address && (
          <div className="mt-4 p-4 bg-gray-50 rounded">
            <p><strong>地址:</strong> {singleResult.formatted_address}</p>
            <p><strong>乡镇/街道:</strong> {singleResult.addressComponent?.township}</p>
          </div>
        )}
      </Card>

      <Card title="批量处理 (Excel/CSV)" variant="borderless">
        <p className="mb-4 text-gray-500">请上传包含"经度"和"纬度"列的 Excel 或 CSV 文件。</p>
        <Upload {...uploadProps('regeo')}>
          <Button icon={<UploadOutlined />}>上传文件并处理</Button>
        </Upload>
      </Card>
    </div>
  );

  const items = [
    { key: '1', label: '地址转经纬度', children: <GeoTab /> },
    { key: '2', label: '经纬度转地址', children: <RegeoTab /> },
  ];

  return (
    <Layout className="min-h-screen">
      <Header className="flex items-center">
        <div className="text-white text-xl font-bold">CoordTrans 经纬度转换工具</div>
      </Header>
      <Content className="p-8 max-w-5xl mx-auto w-full">
        <Tabs
          activeKey={activeTab}
          items={items}
          onChange={(key) => {
            setActiveTab(key);
            setSingleResult(null);
          }}
        />
      </Content>
      <Footer className="text-center">
        CoordTrans ©2024 Created by AI Assistant
      </Footer>
    </Layout>
  );
};

export default App;
