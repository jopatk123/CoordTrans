import React, { useState } from 'react';
import { Layout, Typography, Tabs, Card, Form, Input, Button, Upload, message, Table, Space, Divider } from 'antd';
import { UploadOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Header, Content, Footer } = Layout;
const { Title, Text } = Typography;
const { TextArea } = Input;

const App = () => {
  const [loading, setLoading] = useState(false);
  const [singleResult, setSingleResult] = useState(null);

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
    }
    setLoading(false);
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
    }
    setLoading(false);
  };

  // Batch Upload
  const uploadProps = (type) => ({
    name: 'file',
    action: `/api/batch/file/${type}`,
    headers: {
      authorization: 'authorization-text',
    },
    onChange(info) {
      if (info.file.status !== 'uploading') {
        console.log(info.file, info.fileList);
      }
      if (info.file.status === 'done') {
        message.success(`${info.file.name} 处理成功`);
        // Trigger download
        const url = window.URL.createObjectURL(new Blob([info.file.response]));
        // Note: Antd upload response handling for blob is tricky, usually better to handle manually
      } else if (info.file.status === 'error') {
        message.error(`${info.file.name} 处理失败`);
      }
    },
    customRequest: async ({ file, onSuccess, onError }) => {
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await axios.post(`/api/batch/file/${type}`, formData, {
          responseType: 'blob',
        });
        // Download file
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `processed_${file.name}.xlsx`);
        document.body.appendChild(link);
        link.click();
        onSuccess("ok");
      } catch (err) {
        onError(err);
      }
    }
  });

  const GeoTab = () => (
    <div className="space-y-6">
      <Card title="单条查询" bordered={false}>
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

      <Card title="批量处理 (Excel/CSV)" bordered={false}>
        <p className="mb-4 text-gray-500">请上传包含"地址"列的 Excel 或 CSV 文件。</p>
        <Upload {...uploadProps('geo')}>
          <Button icon={<UploadOutlined />}>上传文件并处理</Button>
        </Upload>
      </Card>
    </div>
  );

  const RegeoTab = () => (
    <div className="space-y-6">
      <Card title="单条查询" bordered={false}>
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

      <Card title="批量处理 (Excel/CSV)" bordered={false}>
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
        <Tabs defaultActiveKey="1" items={items} onChange={() => setSingleResult(null)} />
      </Content>
      <Footer className="text-center">
        CoordTrans ©2024 Created by AI Assistant
      </Footer>
    </Layout>
  );
};

export default App;
