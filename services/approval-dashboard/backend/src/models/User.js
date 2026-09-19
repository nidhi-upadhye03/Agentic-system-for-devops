const { query } = require('../services/database');

/**
 * User Model
 * Handles all user-related database operations
 */

// Find user by ID
const findById = async (id) => {
  try {
    const result = await query(
      'SELECT * FROM users WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  } catch (error) {
    console.error('Error finding user by ID:', error);
    throw error;
  }
};

// Find user by email
const findByEmail = async (email) => {
  try {
    const result = await query(
      'SELECT * FROM users WHERE email = $1',
      [email]
    );
    return result.rows[0] || null;
  } catch (error) {
    console.error('Error finding user by email:', error);
    throw error;
  }
};

// Find user by username
const findByUsername = async (username) => {
  try {
    const result = await query(
      'SELECT * FROM users WHERE username = $1',
      [username]
    );
    return result.rows[0] || null;
  } catch (error) {
    console.error('Error finding user by username:', error);
    throw error;
  }
};

// Create new user
const create = async (userData) => {
  try {
    const {
      username,
      email,
      password_hash,
      full_name,
      role = 'user',
      department,
      avatar_url
    } = userData;

    const result = await query(
      `INSERT INTO users (username, email, password_hash, full_name, role, department, avatar_url, is_active)
       VALUES ($1, $2, $3, $4, $5, $6, $7, true)
       RETURNING *`,
      [username, email, password_hash, full_name, role, department, avatar_url]
    );

    return result.rows[0];
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
};

// Update user
const update = async (id, userData) => {
  try {
    const {
      full_name,
      department,
      avatar_url,
      role,
      is_active
    } = userData;

    // Build dynamic update query based on provided fields
    const updates = [];
    const values = [];
    let paramCount = 1;

    if (full_name !== undefined) {
      updates.push(`full_name = $${paramCount++}`);
      values.push(full_name);
    }
    if (department !== undefined) {
      updates.push(`department = $${paramCount++}`);
      values.push(department);
    }
    if (avatar_url !== undefined) {
      updates.push(`avatar_url = $${paramCount++}`);
      values.push(avatar_url);
    }
    if (role !== undefined) {
      updates.push(`role = $${paramCount++}`);
      values.push(role);
    }
    if (is_active !== undefined) {
      updates.push(`is_active = $${paramCount++}`);
      values.push(is_active);
    }

    if (updates.length === 0) {
      throw new Error('No fields to update');
    }

    updates.push(`updated_at = CURRENT_TIMESTAMP`);
    values.push(id);

    const result = await query(
      `UPDATE users SET ${updates.join(', ')} WHERE id = $${paramCount} RETURNING *`,
      values
    );

    return result.rows[0];
  } catch (error) {
    console.error('Error updating user:', error);
    throw error;
  }
};

// Get all users (with pagination)
const findAll = async (options = {}) => {
  try {
    const { limit = 50, offset = 0, role, is_active } = options;

    let queryText = 'SELECT * FROM users WHERE 1=1';
    const params = [];
    let paramCount = 1;

    if (role) {
      queryText += ` AND role = $${paramCount++}`;
      params.push(role);
    }

    if (is_active !== undefined) {
      queryText += ` AND is_active = $${paramCount++}`;
      params.push(is_active);
    }

    queryText += ` ORDER BY created_at DESC LIMIT $${paramCount++} OFFSET $${paramCount}`;
    params.push(limit, offset);

    const result = await query(queryText, params);
    return result.rows;
  } catch (error) {
    console.error('Error finding all users:', error);
    throw error;
  }
};

// Delete user (soft delete by setting is_active = false)
const deleteUser = async (id) => {
  try {
    const result = await query(
      'UPDATE users SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE id = $1 RETURNING *',
      [id]
    );
    return result.rows[0];
  } catch (error) {
    console.error('Error deleting user:', error);
    throw error;
  }
};

// Hard delete user (permanently remove)
const hardDelete = async (id) => {
  try {
    const result = await query(
      'DELETE FROM users WHERE id = $1 RETURNING *',
      [id]
    );
    return result.rows[0];
  } catch (error) {
    console.error('Error hard deleting user:', error);
    throw error;
  }
};

// Count users
const count = async (options = {}) => {
  try {
    const { role, is_active } = options;

    let queryText = 'SELECT COUNT(*) FROM users WHERE 1=1';
    const params = [];
    let paramCount = 1;

    if (role) {
      queryText += ` AND role = $${paramCount++}`;
      params.push(role);
    }

    if (is_active !== undefined) {
      queryText += ` AND is_active = $${paramCount}`;
      params.push(is_active);
    }

    const result = await query(queryText, params);
    return parseInt(result.rows[0].count, 10);
  } catch (error) {
    console.error('Error counting users:', error);
    throw error;
  }
};

module.exports = {
  findById,
  findByEmail,
  findByUsername,
  create,
  update,
  findAll,
  deleteUser,
  hardDelete,
  count
};
