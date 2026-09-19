const { query } = require('../services/database');

const Approval = {
  async create(data) {
    const {
      title,
      description,
      request_type,
      priority,
      requested_by,
      approved_by,
      metadata,
      due_date
    } = data;

    const sql = `
      INSERT INTO approvals (
        title, description, request_type, priority, requested_by, 
        approved_by, metadata
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `;

    const values = [
      title, description, request_type, priority, requested_by,
      approved_by, metadata
    ];

    const result = await query(sql, values);
    return result.rows[0];
  },

  async findAll(filters = {}, limit = 50, offset = 0) {
    let sql = `
      SELECT a.*, 
             u1.full_name as requester_name, u1.email as requester_email,
             u2.full_name as approver_name, u2.email as approver_email
      FROM approvals a
      LEFT JOIN users u1 ON a.requested_by = u1.id
      LEFT JOIN users u2 ON a.approved_by = u2.id
      WHERE 1=1
    `;
    
    const values = [];
    let paramIndex = 1;

    if (filters.status) {
      sql += ` AND a.status = $${paramIndex++}`;
      values.push(filters.status);
    }
    
    if (filters.request_type) {
      sql += ` AND a.request_type = $${paramIndex++}`;
      values.push(filters.request_type);
    }
    
    if (filters.priority) {
      sql += ` AND a.priority = $${paramIndex++}`;
      values.push(filters.priority);
    }
    
    if (filters.requested_by) {
      sql += ` AND a.requested_by = $${paramIndex++}`;
      values.push(filters.requested_by);
    }
    
    if (filters.approved_by) {
      sql += ` AND a.approved_by = $${paramIndex++}`;
      values.push(filters.approved_by);
    }

    sql += ` ORDER BY a.created_at DESC LIMIT $${paramIndex++} OFFSET $${paramIndex++}`;
    values.push(limit, offset);

    const result = await query(sql, values);
    return result.rows;
  },

  async findById(id) {
    const sql = `
      SELECT a.*, 
             u1.full_name as requester_name, u1.email as requester_email,
             u2.full_name as approver_name, u2.email as approver_email
      FROM approvals a
      LEFT JOIN users u1 ON a.requested_by = u1.id
      LEFT JOIN users u2 ON a.approved_by = u2.id
      WHERE a.id = $1
    `;
    
    const result = await query(sql, [id]);
    return result.rows[0];
  },

  async update(id, updates) {
    const allowedUpdates = ['title', 'description', 'priority', 'metadata', 'attachments', 'due_date'];
    const values = [];
    let sql = 'UPDATE approvals SET updated_at = NOW()';
    let paramIndex = 1;

    for (const key of Object.keys(updates)) {
      if (allowedUpdates.includes(key)) {
        sql += `, ${key} = $${paramIndex++}`;
        values.push(updates[key]);
      }
    }

    sql += ` WHERE id = $${paramIndex} RETURNING *`;
    values.push(id);

    const result = await query(sql, values);
    return result.rows[0];
  },

  async updateStatus(id, status, comments) {
    const sql = `
      UPDATE approvals 
      SET status = $1::text, 
          updated_at = NOW(),
          approved_at = CASE WHEN $1::text = 'approved' THEN NOW() ELSE approved_at END,
          rejected_at = CASE WHEN $1::text = 'rejected' THEN NOW() ELSE rejected_at END,
          rejection_reason = CASE WHEN $1::text = 'rejected' THEN $2 ELSE rejection_reason END
      WHERE id = $3
      RETURNING *
    `;
    
    const result = await query(sql, [status, comments, id]);
    return result.rows[0];
  },

  async delete(id) {
    await query('DELETE FROM approvals WHERE id = $1', [id]);
    return true;
  },

  async getStats(userId, role) {
    let sql = `
      SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
      FROM approvals
    `;
    
    const values = [];
    
    if (role !== 'admin') {
      sql += ` WHERE requested_by = $1 OR approved_by = $1`;
      values.push(userId);
    }

    const result = await query(sql, values);
    return result.rows[0];
  },

  async search(q, filters = {}, limit = 50) {
    let sql = `
      SELECT a.*, 
             u1.full_name as requester_name, u1.email as requester_email,
             u2.full_name as approver_name, u2.email as approver_email
      FROM approvals a
      LEFT JOIN users u1 ON a.requested_by = u1.id
      LEFT JOIN users u2 ON a.approved_by = u2.id
      WHERE (a.title ILIKE $1 OR a.description ILIKE $1)
    `;
    
    const values = [`%${q}%`];
    let paramIndex = 2;

    if (filters.status) {
      sql += ` AND a.status = $${paramIndex++}`;
      values.push(filters.status);
    }
    
    if (filters.request_type) {
      sql += ` AND a.request_type = $${paramIndex++}`;
      values.push(filters.request_type);
    }

    sql += ` ORDER BY a.created_at DESC LIMIT $${paramIndex}`;
    values.push(limit);

    const result = await query(sql, values);
    return result.rows;
  },

  async addHistory(approvalId, userId, action, oldStatus, newStatus, comments) {
    const sql = `
      INSERT INTO approval_history (
        approval_id, user_id, action, old_status, new_status, comments
      )
      VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING *
    `;
    
    const values = [approvalId, userId, action, oldStatus, newStatus, comments];
    const result = await query(sql, values);
    return result.rows[0];
  },

  async getHistory(approvalId) {
    const sql = `
      SELECT h.*, u.full_name as user_name, u.email as user_email
      FROM approval_history h
      LEFT JOIN users u ON h.user_id = u.id
      WHERE h.approval_id = $1
      ORDER BY h.created_at DESC
    `;
    
    const result = await query(sql, [approvalId]);
    return result.rows;
  }
};

module.exports = Approval;

