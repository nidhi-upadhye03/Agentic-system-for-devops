import React from 'react';
import { motion } from 'framer-motion';
import { Database, HeartHandshake, Sparkles } from 'lucide-react';
import { Box, Typography, Chip } from '@mui/material';

const AgentWorkflow = ({
  circleText = "AI",
  badgeTexts = {
    first: "Monitor",
    second: "Analyze",
    third: "Respond",
    fourth: "Notify"
  },
  buttonTexts = {
    first: "DevOps Agent",
    second: "v1.0.0"
  },
  title = "Autonomous Agent Workflow - Event-Driven Incident Response",
  lightColor = "#3b82f6"
}) => {
  return (
    <Box
      sx={{
        position: 'relative',
        display: 'flex',
        height: '500px',
        width: '100%',
        maxWidth: '800px',
        flexDirection: 'column',
        alignItems: 'center',
        margin: '0 auto'
      }}
    >
      {/* SVG Paths */}
      <svg
        style={{ height: '100%', width: '100%', color: '#475569' }}
        width="100%"
        height="100%"
        viewBox="0 0 200 100"
      >
        <g
          stroke="currentColor"
          fill="none"
          strokeWidth="0.4"
          strokeDasharray="100 100"
          pathLength="100"
        >
          <path d="M 31 10 v 15 q 0 5 5 5 h 59 q 5 0 5 5 v 10" />
          <path d="M 77 10 v 10 q 0 5 5 5 h 13 q 5 0 5 5 v 10" />
          <path d="M 124 10 v 10 q 0 5 -5 5 h -14 q -5 0 -5 5 v 10" />
          <path d="M 170 10 v 15 q 0 5 -5 5 h -60 q -5 0 -5 5 v 10" />
          {/* Animation For Path Starting */}
          <animate
            attributeName="stroke-dashoffset"
            from="100"
            to="0"
            dur="1s"
            fill="freeze"
            calcMode="spline"
            keySplines="0.25,0.1,0.5,1"
            keyTimes="0; 1"
          />
        </g>
        {/* Blue Lights */}
        <g mask="url(#db-mask-1)">
          <circle
            className="database db-light-1"
            cx="0"
            cy="0"
            r="12"
            fill="url(#db-blue-grad)"
          />
        </g>
        <g mask="url(#db-mask-2)">
          <circle
            className="database db-light-2"
            cx="0"
            cy="0"
            r="12"
            fill="url(#db-blue-grad)"
          />
        </g>
        <g mask="url(#db-mask-3)">
          <circle
            className="database db-light-3"
            cx="0"
            cy="0"
            r="12"
            fill="url(#db-blue-grad)"
          />
        </g>
        <g mask="url(#db-mask-4)">
          <circle
            className="database db-light-4"
            cx="0"
            cy="0"
            r="12"
            fill="url(#db-blue-grad)"
          />
        </g>
        {/* Buttons */}
        <g stroke="currentColor" fill="none" strokeWidth="0.4">
          {/* First Button - Monitoring */}
          <g>
            <rect
              fill="#1e293b"
              x="14"
              y="5"
              width="34"
              height="10"
              rx="5"
            />
            <DatabaseIcon x="18" y="7.5" />
            <text
              x="26"
              y="12"
              fill="white"
              stroke="none"
              fontSize="4.5"
              fontWeight="500"
            >
              {badgeTexts.first}
            </text>
          </g>
          {/* Second Button - Analyzer */}
          <g>
            <rect
              fill="#1e293b"
              x="60"
              y="5"
              width="34"
              height="10"
              rx="5"
            />
            <DatabaseIcon x="64" y="7.5" />
            <text
              x="72"
              y="12"
              fill="white"
              stroke="none"
              fontSize="4.5"
              fontWeight="500"
            >
              {badgeTexts.second}
            </text>
          </g>
          {/* Third Button - Auto Response */}
          <g>
            <rect
              fill="#1e293b"
              x="106"
              y="5"
              width="36"
              height="10"
              rx="5"
            />
            <DatabaseIcon x="110" y="7.5" />
            <text
              x="118"
              y="12"
              fill="white"
              stroke="none"
              fontSize="4.5"
              fontWeight="500"
            >
              {badgeTexts.third}
            </text>
          </g>
          {/* Fourth Button - Notifier */}
          <g>
            <rect
              fill="#1e293b"
              x="154"
              y="5"
              width="36"
              height="10"
              rx="5"
            />
            <DatabaseIcon x="158" y="7.5" />
            <text
              x="166"
              y="12"
              fill="white"
              stroke="none"
              fontSize="4.5"
              fontWeight="500"
            >
              {badgeTexts.fourth}
            </text>
          </g>
        </g>
        <defs>
          {/* Masks for animation paths */}
          <mask id="db-mask-1">
            <path
              d="M 31 10 v 15 q 0 5 5 5 h 59 q 5 0 5 5 v 10"
              strokeWidth="0.5"
              stroke="white"
            />
          </mask>
          <mask id="db-mask-2">
            <path
              d="M 77 10 v 10 q 0 5 5 5 h 13 q 5 0 5 5 v 10"
              strokeWidth="0.5"
              stroke="white"
            />
          </mask>
          <mask id="db-mask-3">
            <path
              d="M 124 10 v 10 q 0 5 -5 5 h -14 q -5 0 -5 5 v 10"
              strokeWidth="0.5"
              stroke="white"
            />
          </mask>
          <mask id="db-mask-4">
            <path
              d="M 170 10 v 15 q 0 5 -5 5 h -60 q -5 0 -5 5 v 10"
              strokeWidth="0.5"
              stroke="white"
            />
          </mask>
          {/* Blue Gradient */}
          <radialGradient id="db-blue-grad" fx="1">
            <stop offset="0%" stopColor={lightColor} />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>
      </svg>

      {/* Main Box */}
      <Box
        sx={{
          position: 'absolute',
          bottom: '40px',
          display: 'flex',
          width: '100%',
          flexDirection: 'column',
          alignItems: 'center'
        }}
      >
        {/* Bottom shadow */}
        <Box
          sx={{
            position: 'absolute',
            bottom: '-16px',
            height: '100px',
            width: '62%',
            borderRadius: '8px',
            bgcolor: 'rgba(59, 130, 246, 0.1)'
          }}
        />

        {/* Box title */}
        <Box
          sx={{
            position: 'absolute',
            top: '-16px',
            zIndex: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '8px',
            border: '1px solid #334155',
            bgcolor: '#0f172a',
            px: 3,
            py: 1.5
          }}
        >
          <Sparkles size={20} color="#3b82f6" />
          <Typography variant="body2" sx={{ ml: 1.5, fontSize: '13px', fontWeight: 500 }}>
            {title}
          </Typography>
        </Box>

        {/* Box outer circle */}
        <Box
          sx={{
            position: 'absolute',
            bottom: '-40px',
            zIndex: 30,
            display: 'grid',
            placeItems: 'center',
            height: '80px',
            width: '80px',
            borderRadius: '50%',
            borderTop: '1px solid #334155',
            bgcolor: '#1e293b',
            fontWeight: 600,
            fontSize: '16px'
          }}
        >
          {circleText}
        </Box>

        {/* Box content */}
        <Box
          sx={{
            position: 'relative',
            zIndex: 10,
            display: 'flex',
            height: '220px',
            width: '100%',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            borderRadius: '12px',
            border: '2px solid #334155',
            bgcolor: '#1e293b',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.7)'
          }}
        >
          {/* Badges */}
          <Chip
            icon={<HeartHandshake size={18} />}
            label={buttonTexts.first}
            sx={{
              position: 'absolute',
              bottom: '40px',
              left: '60px',
              zIndex: 10,
              bgcolor: '#0f172a',
              border: '1px solid #334155',
              color: 'white',
              fontSize: '14px',
              height: '36px',
              px: 1
            }}
          />
          <Chip
            icon={<Database size={18} />}
            label={buttonTexts.second}
            sx={{
              position: 'absolute',
              right: '80px',
              zIndex: 10,
              bgcolor: '#0f172a',
              border: '1px solid #334155',
              color: 'white',
              fontSize: '14px',
              height: '36px',
              px: 1,
              display: { xs: 'none', sm: 'flex' }
            }}
          />

          {/* Animated circles */}
          <motion.div
            style={{
              position: 'absolute',
              bottom: '-70px',
              height: '140px',
              width: '140px',
              borderRadius: '50%',
              borderTop: '2px solid rgba(59, 130, 246, 0.3)',
              background: 'rgba(59, 130, 246, 0.08)'
            }}
            animate={{
              scale: [0.98, 1.02, 0.98, 1, 1, 1, 1, 1, 1],
            }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <motion.div
            style={{
              position: 'absolute',
              bottom: '-100px',
              height: '200px',
              width: '200px',
              borderRadius: '50%',
              borderTop: '2px solid rgba(59, 130, 246, 0.3)',
              background: 'rgba(59, 130, 246, 0.08)'
            }}
            animate={{
              scale: [1, 1, 1, 0.98, 1.02, 0.98, 1, 1, 1],
            }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <motion.div
            style={{
              position: 'absolute',
              bottom: '-130px',
              height: '260px',
              width: '260px',
              borderRadius: '50%',
              borderTop: '2px solid rgba(59, 130, 246, 0.3)',
              background: 'rgba(59, 130, 246, 0.08)'
            }}
            animate={{
              scale: [1, 1, 1, 1, 1, 0.98, 1.02, 0.98, 1, 1],
            }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <motion.div
            style={{
              position: 'absolute',
              bottom: '-160px',
              height: '320px',
              width: '320px',
              borderRadius: '50%',
              borderTop: '2px solid rgba(59, 130, 246, 0.3)',
              background: 'rgba(59, 130, 246, 0.08)'
            }}
            animate={{
              scale: [1, 1, 1, 1, 1, 1, 0.98, 1.02, 0.98, 1],
            }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        </Box>
      </Box>
    </Box>
  );
};

const DatabaseIcon = ({ x = "0", y = "0" }) => {
  return (
    <svg
      x={x}
      y={y}
      xmlns="http://www.w3.org/2000/svg"
      width="5"
      height="5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="white"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5V19A9 3 0 0 0 21 19V5" />
      <path d="M3 12A9 3 0 0 0 21 12" />
    </svg>
  );
};

export default AgentWorkflow;
