import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { contactAPI, handleApiError } from '../services/api';

const ContactForm = ({ onClose, preFilledData = {} }) => {
  const [formData, setFormData] = useState({
    name: preFilledData.name || '',
    email: preFilledData.email || '',
    subject: preFilledData.subject || '',
    message: preFilledData.message || '',
    availability_preference: preFilledData.availability_preference || ''
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null); // 'success', 'error', null
  const [errorMessage, setErrorMessage] = useState('');

  const handleInputChange = (name, value) => {
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus(null);
    setErrorMessage('');

    try {
      const response = await contactAPI.submitMessage(formData);
      
      if (response.success) {
        setSubmitStatus('success');
        setFormData({
          name: '',
          email: '',
          subject: '',
          message: '',
          availability_preference: ''
        });
      } else {
        setSubmitStatus('error');
        setErrorMessage(response.message || 'Failed to send message');
      }
    } catch (error) {
      setSubmitStatus('error');
      setErrorMessage(handleApiError(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitStatus === 'success') {
    return (
      <Card className="w-full max-w-md mx-auto contact-form bg-white">
        <CardContent className="p-6 text-center bg-white">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Message Sent!</h3>
          <p className="text-gray-600 mb-4">
            Thank you for reaching out. I'll get back to you within 24 hours.
          </p>
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto contact-form bg-white">
      <CardHeader>
        <CardTitle className="text-lg font-medium">Get in Touch</CardTitle>
        <CardDescription>
          Available 8am to 5pm CST for consultation
        </CardDescription>
      </CardHeader>
      
      <CardContent className="bg-white">
        <form onSubmit={handleSubmit} className="space-y-4">
          {submitStatus === 'error' && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
          
          <div>
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              required
              disabled={isSubmitting}
              placeholder="Your full name"
            />
          </div>
          
          <div>
            <Label htmlFor="email">Email *</Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
              required
              disabled={isSubmitting}
              placeholder="your.email@example.com"
            />
          </div>
          
          <div>
            <Label htmlFor="subject">Subject *</Label>
            <Input
              id="subject"
              value={formData.subject}
              onChange={(e) => handleInputChange('subject', e.target.value)}
              required
              disabled={isSubmitting}
              placeholder="What's this about?"
            />
          </div>
          
          <div>
            <Label htmlFor="availability">Preferred Meeting Time</Label>
            <Select
              value={formData.availability_preference}
              onValueChange={(value) => handleInputChange('availability_preference', value)}
              disabled={isSubmitting}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select your preference" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="morning">Morning (8am - 12pm CST)</SelectItem>
                <SelectItem value="afternoon">Afternoon (12pm - 5pm CST)</SelectItem>
                <SelectItem value="flexible">I'm flexible</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label htmlFor="message">Message *</Label>
            <Textarea
              id="message"
              value={formData.message}
              onChange={(e) => handleInputChange('message', e.target.value)}
              required
              disabled={isSubmitting}
              placeholder="Tell me about your project or how I can help..."
              rows={4}
            />
          </div>
          
          <div className="flex gap-2">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                'Send Message'
              )}
            </Button>
            
            {onClose && (
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default ContactForm;