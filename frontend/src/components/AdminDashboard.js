import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Alert, AlertDescription } from './ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  Mail, 
  Clock, 
  User, 
  MessageSquare, 
  Trash2, 
  Eye, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  Download,
  RefreshCw,
  BarChart3
} from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminDashboard = () => {
  const [messages, setMessages] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [updatingMessage, setUpdatingMessage] = useState(null);

  // Load dashboard data
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load messages and stats in parallel
      const [messagesResponse, statsResponse] = await Promise.all([
        axios.get(`${API}/admin/messages`, {
          params: selectedStatus !== 'all' ? { status: selectedStatus } : {}
        }),
        axios.get(`${API}/admin/dashboard/stats`)
      ]);
      
      setMessages(messagesResponse.data.messages);
      setStats(statsResponse.data);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Update message status
  const updateMessageStatus = async (messageId, newStatus) => {
    try {
      setUpdatingMessage(messageId);
      
      await axios.put(`${API}/admin/messages/${messageId}/status?new_status=${newStatus}`);
      
      // Update local state
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, status: newStatus } : msg
      ));
      
      // Reload stats
      const statsResponse = await axios.get(`${API}/admin/dashboard/stats`);
      setStats(statsResponse.data);
      
    } catch (err) {
      setError('Failed to update message status');
      console.error('Update error:', err);
    } finally {
      setUpdatingMessage(null);
    }
  };

  // Delete message
  const deleteMessage = async (messageId) => {
    if (!window.confirm('Are you sure you want to delete this message?')) {
      return;
    }
    
    try {
      await axios.delete(`${API}/admin/messages/${messageId}`);
      
      // Remove from local state
      setMessages(prev => prev.filter(msg => msg.id !== messageId));
      
      // Reload stats
      const statsResponse = await axios.get(`${API}/admin/dashboard/stats`);
      setStats(statsResponse.data);
      
    } catch (err) {
      setError('Failed to delete message');
      console.error('Delete error:', err);
    }
  };

  // Export messages
  const exportMessages = async () => {
    try {
      const response = await axios.get(`${API}/admin/messages/export`);
      
      // Create and download file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `portfolio-messages-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
    } catch (err) {
      setError('Failed to export messages');
      console.error('Export error:', err);
    }
  };

  // Format date
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'new': return 'bg-yellow-100 text-yellow-800';
      case 'read': return 'bg-blue-100 text-blue-800';
      case 'responded': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Load data on component mount and when filter changes
  useEffect(() => {
    loadDashboardData();
  }, [selectedStatus]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin mr-2" />
        <span>Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-600">Manage your portfolio contact messages</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={loadDashboardData} variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={exportMessages} variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Messages</CardTitle>
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_messages}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">New Messages</CardTitle>
                <Mail className="h-4 w-4 text-yellow-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {stats.status_breakdown.new || 0}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Recent (7 days)</CardTitle>
                <Clock className="h-4 w-4 text-blue-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  {stats.recent_messages_7_days}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Responded</CardTitle>
                <CheckCircle className="h-4 w-4 text-green-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {stats.status_breakdown.responded || 0}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Messages Section */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Contact Messages</CardTitle>
                <CardDescription>
                  Messages from your portfolio contact form
                </CardDescription>
              </div>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Messages</SelectItem>
                  <SelectItem value="new">New</SelectItem>
                  <SelectItem value="read">Read</SelectItem>
                  <SelectItem value="responded">Responded</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          
          <CardContent>
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No messages found</p>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <Card key={message.id} className="border-l-4 border-l-blue-500">
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <User className="w-4 h-4" />
                            <span className="font-medium">{message.name}</span>
                            <span className="text-gray-500">({message.email})</span>
                            <Badge className={getStatusColor(message.status)}>
                              {message.status}
                            </Badge>
                          </div>
                          
                          <h3 className="font-medium text-lg mb-2">{message.subject}</h3>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 mb-4">
                            <div>
                              <strong>Submitted:</strong> {formatDate(message.submitted_at)}
                            </div>
                            <div>
                              <strong>Availability:</strong> {message.availability_preference || 'No preference'}
                            </div>
                          </div>
                          
                          <div className="bg-gray-50 p-3 rounded-md">
                            <p className="whitespace-pre-wrap">{message.message}</p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center pt-4 border-t">
                        <div className="flex gap-2">
                          {message.status === 'new' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => updateMessageStatus(message.id, 'read')}
                              disabled={updatingMessage === message.id}
                            >
                              {updatingMessage === message.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Eye className="w-4 h-4 mr-1" />
                              )}
                              Mark as Read
                            </Button>
                          )}
                          
                          {message.status !== 'responded' && (
                            <Button
                              size="sm"
                              onClick={() => updateMessageStatus(message.id, 'responded')}
                              disabled={updatingMessage === message.id}
                            >
                              {updatingMessage === message.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <CheckCircle className="w-4 h-4 mr-1" />
                              )}
                              Mark as Responded
                            </Button>
                          )}
                        </div>
                        
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => window.open(`mailto:${message.email}?subject=Re: ${message.subject}`)}
                          >
                            <Mail className="w-4 h-4 mr-1" />
                            Reply
                          </Button>
                          
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => deleteMessage(message.id)}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminDashboard;