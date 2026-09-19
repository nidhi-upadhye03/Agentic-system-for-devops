const nodemailer = require('nodemailer');
const sgMail = require('@sendgrid/mail');
const config = require('../config/config');

// Initialize email provider
let transporter;

if (config.email.provider === 'sendgrid') {
  sgMail.setApiKey(config.email.sendgrid.apiKey);
} else {
  // SMTP configuration
  transporter = nodemailer.createTransport({
    host: config.email.smtp.host,
    port: config.email.smtp.port,
    secure: config.email.smtp.secure,
    auth: {
      user: config.email.smtp.auth.user,
      pass: config.email.smtp.auth.pass
    }
  });
}

// Send email using SMTP
const sendEmailSMTP = async (to, subject, html) => {
  try {
    const mailOptions = {
      from: `${config.email.fromName} <${config.email.from}>`,
      to,
      subject,
      html
    };

    const info = await transporter.sendMail(mailOptions);
    console.log('Email sent:', info.messageId);
    return { success: true, messageId: info.messageId };
  } catch (error) {
    console.error('SMTP email error:', error);
    throw error;
  }
};

// Send email using SendGrid
const sendEmailSendGrid = async (to, subject, html) => {
  try {
    const msg = {
      to,
      from: {
        email: config.email.from,
        name: config.email.fromName
      },
      subject,
      html
    };

    await sgMail.send(msg);
    console.log('Email sent via SendGrid');
    return { success: true };
  } catch (error) {
    console.error('SendGrid email error:', error);
    throw error;
  }
};

// Generic send email function
const sendEmail = async (to, subject, html) => {
  if (config.email.provider === 'sendgrid') {
    return sendEmailSendGrid(to, subject, html);
  } else {
    return sendEmailSMTP(to, subject, html);
  }
};

// Email templates
const getApprovalNotificationTemplate = (approverName, requesterName, approvalTitle, approvalId) => {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>New Approval Request</h1>
        </div>
        <div class="content">
          <p>Hi ${approverName},</p>
          <p><strong>${requesterName}</strong> has submitted a new approval request that requires your attention:</p>
          <h3>${approvalTitle}</h3>
          <p>Please review and take action on this request.</p>
          <a href="${config.server.corsOrigin}/approvals/${approvalId}" class="button">View Approval Request</a>
        </div>
        <div class="footer">
          <p>This is an automated message from ${config.app.name}.</p>
          <p>Please do not reply to this email.</p>
        </div>
      </div>
    </body>
    </html>
  `;
};

const getApprovalStatusUpdateTemplate = (requesterName, approvalTitle, status, comments, approvalId) => {
  const statusColor = status === 'approved' ? '#4CAF50' : '#f44336';
  const statusText = status === 'approved' ? 'Approved' : 'Rejected';

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: ${statusColor}; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .status { font-size: 24px; font-weight: bold; color: ${statusColor}; margin: 10px 0; }
        .button { display: inline-block; padding: 12px 24px; background: ${statusColor}; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }
        .comments { background: white; padding: 15px; border-left: 4px solid ${statusColor}; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Approval Request Update</h1>
        </div>
        <div class="content">
          <p>Hi ${requesterName},</p>
          <p>Your approval request has been reviewed:</p>
          <h3>${approvalTitle}</h3>
          <div class="status">${statusText}</div>
          ${comments ? `<div class="comments"><strong>Comments:</strong><br>${comments}</div>` : ''}
          <a href="${config.server.corsOrigin}/approvals/${approvalId}" class="button">View Details</a>
        </div>
        <div class="footer">
          <p>This is an automated message from ${config.app.name}.</p>
          <p>Please do not reply to this email.</p>
        </div>
      </div>
    </body>
    </html>
  `;
};

// Send approval notification to approver
const sendApprovalNotification = async (approverEmail, approverName, requesterName, approvalTitle, approvalId) => {
  const subject = 'New Approval Request';
  const html = getApprovalNotificationTemplate(approverName, requesterName, approvalTitle, approvalId);
  return sendEmail(approverEmail, subject, html);
};

// Send approval status update to requester
const sendApprovalStatusUpdate = async (requesterEmail, requesterName, approvalTitle, status, comments, approvalId) => {
  const subject = `Approval Request ${status === 'approved' ? 'Approved' : 'Rejected'}`;
  const html = getApprovalStatusUpdateTemplate(requesterName, approvalTitle, status, comments, approvalId);
  return sendEmail(requesterEmail, subject, html);
};

// Send welcome email
const sendWelcomeEmail = async (userEmail, userName) => {
  const subject = `Welcome to ${config.app.name}`;
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Welcome to ${config.app.name}</h1>
        </div>
        <div class="content">
          <p>Hi ${userName},</p>
          <p>Thank you for registering! Your account has been successfully created.</p>
          <p>You can now submit and manage approval requests through our platform.</p>
          <a href="${config.server.corsOrigin}" class="button">Get Started</a>
        </div>
        <div class="footer">
          <p>This is an automated message from ${config.app.name}.</p>
          <p>Please do not reply to this email.</p>
        </div>
      </div>
    </body>
    </html>
  `;
  return sendEmail(userEmail, subject, html);
};

module.exports = {
  sendEmail,
  sendApprovalNotification,
  sendApprovalStatusUpdate,
  sendWelcomeEmail
};
