/**
 * RabbitMQ Event Publisher
 * Publishes approval decisions to RabbitMQ for consumption by auto-response agent
 */
const amqp = require('amqplib');

class EventPublisher {
  constructor() {
    this.connection = null;
    this.channel = null;
    this.exchange = process.env.RABBITMQ_EXCHANGE || 'devops_events';
    this.connecting = false;
  }

  async connect() {
    if (this.connection || this.connecting) {
      return;
    }

    this.connecting = true;

    try {
      const host = process.env.RABBITMQ_HOST || 'rabbitmq';
      const port = process.env.RABBITMQ_PORT || 5672;
      const user = process.env.RABBITMQ_USER || 'guest';
      const password = process.env.RABBITMQ_PASSWORD || 'guest';
      const vhost = process.env.RABBITMQ_VHOST || '/';

      // Construct URL with proper vhost encoding
      const vhostPath = vhost === '/' ? '/' : `/${encodeURIComponent(vhost)}`;
      const url = `amqp://${user}:${password}@${host}:${port}${vhostPath}`;

      console.log(`Connecting to RabbitMQ at ${host}:${port}...`);
      this.connection = await amqp.connect(url);
      this.channel = await this.connection.createChannel();

      // Declare exchange
      await this.channel.assertExchange(this.exchange, 'topic', { durable: true });

      console.log('✓ RabbitMQ event publisher connected');

      // Handle connection errors
      this.connection.on('error', (err) => {
        console.error('RabbitMQ connection error:', err.message);
      });

      this.connection.on('close', () => {
        console.log('RabbitMQ connection closed');
        this.connection = null;
        this.channel = null;
        // Attempt reconnection after delay
        setTimeout(() => this.connect(), 5000);
      });
    } catch (error) {
      console.error('Failed to connect to RabbitMQ:', error.message);
      this.connection = null;
      this.channel = null;
      // Retry connection after delay
      setTimeout(() => this.connect(), 5000);
    } finally {
      this.connecting = false;
    }
  }

  async publishApprovalDecision(approvalId, decision, approvalData) {
    if (!this.channel) {
      console.warn('RabbitMQ not connected, cannot publish approval decision');
      return;
    }

    try {
      const message = {
        event_type: 'approval_decision',
        approval_id: approvalId,
        decision: decision, // 'approved' or 'rejected'
        timestamp: new Date().toISOString(),
        data: approvalData
      };

      const routingKey = `approval.${decision}`;
      
      this.channel.publish(
        this.exchange,
        routingKey,
        Buffer.from(JSON.stringify(message)),
        { persistent: true }
      );

      console.log(`✓ Published approval decision: ${approvalId} - ${decision}`);
    } catch (error) {
      console.error('Failed to publish approval decision:', error.message);
    }
  }

  async disconnect() {
    try {
      if (this.channel) {
        await this.channel.close();
      }
      if (this.connection) {
        await this.connection.close();
      }
      console.log('✓ RabbitMQ event publisher disconnected');
    } catch (error) {
      console.error('Error disconnecting from RabbitMQ:', error.message);
    }
  }
}

// Singleton instance
const eventPublisher = new EventPublisher();

// Auto-connect on module load
eventPublisher.connect().catch(err => {
  console.error('Failed to initialize RabbitMQ publisher:', err);
});

module.exports = eventPublisher;
