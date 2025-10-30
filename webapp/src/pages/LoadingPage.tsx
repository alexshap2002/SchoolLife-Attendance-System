import React from 'react'
import { motion } from 'framer-motion'

const LoadingPage: React.FC = () => {
  return (
    <div className="h-screen flex items-center justify-center bg-telegram-bg">
      <motion.div
        className="text-center"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* Logo */}
        <motion.div
          className="text-6xl mb-6"
          animate={{ 
            rotate: [0, 10, -10, 0],
            scale: [1, 1.1, 1]
          }}
          transition={{ 
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          📝
        </motion.div>

        {/* Title */}
        <h1 className="text-2xl font-bold text-telegram-text mb-2">
          Відмітка присутності
        </h1>
        
        <p className="text-telegram-hint mb-8">
          School of Life Brusyliv
        </p>

        {/* Loading animation */}
        <div className="flex justify-center space-x-2">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-3 h-3 bg-telegram-link rounded-full"
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.2
              }}
            />
          ))}
        </div>

        {/* Subtitle */}
        <motion.p
          className="text-sm text-telegram-hint mt-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          Ініціалізація Telegram WebApp...
        </motion.p>
      </motion.div>
    </div>
  )
}

export default LoadingPage
