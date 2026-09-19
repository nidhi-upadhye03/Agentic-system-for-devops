const bcrypt = require('bcrypt');
const db = require('../src/services/database');

async function main() {
  const [,, email, password] = process.argv;
  if (!email || !password) {
    console.error('Usage: node scripts/setPassword.js <email> <password>');
    process.exit(1);
  }

  try {
    const hash = await bcrypt.hash(password, 10);
    await db.query('UPDATE users SET password_hash = $1 WHERE email = $2', [hash, email]);
    console.log(`Password updated for ${email}`);
    process.exit(0);
  } catch (err) {
    console.error('Error updating password:', err);
    process.exit(2);
  }
}

main();
