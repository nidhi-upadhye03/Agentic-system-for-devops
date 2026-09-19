require('dotenv').config();
const { query, testConnection, initializeTables } = require('../services/database');
const bcrypt = require('bcrypt');

// Create initial admin user
const createAdminUser = async () => {
  try {
    // Check if admin exists
    const existingAdmin = await query(
      'SELECT id FROM users WHERE email = $1',
      ['admin@approvaldashboard.com']
    );

    if (existingAdmin.rows.length > 0) {
      console.log('Admin user already exists');
      return;
    }

    // Create admin user
    const password_hash = await bcrypt.hash('Admin@123', 10);
    const result = await query(
      `INSERT INTO users (username, email, password_hash, full_name, role)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, username, email, role`,
      ['admin', 'admin@approvaldashboard.com', password_hash, 'System Administrator', 'admin']
    );

    console.log('Admin user created successfully:', result.rows[0]);
  } catch (error) {
    console.error('Error creating admin user:', error);
    throw error;
  }
};

// Create sample users
const createSampleUsers = async () => {
  try {
    const sampleUsers = [
      {
        username: 'john_doe',
        email: 'john@example.com',
        password: 'User@123',
        full_name: 'John Doe',
        role: 'user',
        department: 'Engineering'
      },
      {
        username: 'jane_smith',
        email: 'jane@example.com',
        password: 'Approver@123',
        full_name: 'Jane Smith',
        role: 'approver',
        department: 'Management'
      },
      {
        username: 'bob_johnson',
        email: 'bob@example.com',
        password: 'User@123',
        full_name: 'Bob Johnson',
        role: 'user',
        department: 'DevOps'
      }
    ];

    for (const user of sampleUsers) {
      // Check if user exists
      const existing = await query('SELECT id FROM users WHERE email = $1', [user.email]);

      if (existing.rows.length === 0) {
        const password_hash = await bcrypt.hash(user.password, 10);
        await query(
          `INSERT INTO users (username, email, password_hash, full_name, role, department)
           VALUES ($1, $2, $3, $4, $5, $6)`,
          [user.username, user.email, password_hash, user.full_name, user.role, user.department]
        );
        console.log(`Sample user created: ${user.username}`);
      } else {
        console.log(`Sample user already exists: ${user.username}`);
      }
    }
  } catch (error) {
    console.error('Error creating sample users:', error);
    throw error;
  }
};

// Main migration function
const runMigrations = async () => {
  console.log('Starting database migrations...');
  console.log('='.repeat(50));

  try {
    // Test connection
    console.log('1. Testing database connection...');
    const connected = await testConnection();
    if (!connected) {
      throw new Error('Failed to connect to database');
    }

    // Initialize tables
    console.log('2. Initializing database tables...');
    await initializeTables();

    // Create admin user
    console.log('3. Creating admin user...');
    await createAdminUser();

    // Create sample users (optional - comment out for production)
    if (process.env.NODE_ENV === 'development') {
      console.log('4. Creating sample users...');
      await createSampleUsers();
    }

    console.log('='.repeat(50));
    console.log('Database migrations completed successfully!');
    console.log('\nDefault credentials:');
    console.log('Admin: admin@approvaldashboard.com / Admin@123');
    if (process.env.NODE_ENV === 'development') {
      console.log('User: john@example.com / User@123');
      console.log('Approver: jane@example.com / Approver@123');
    }
    console.log('='.repeat(50));

    process.exit(0);
  } catch (error) {
    console.error('Migration failed:', error);
    process.exit(1);
  }
};

// Run migrations
runMigrations();
