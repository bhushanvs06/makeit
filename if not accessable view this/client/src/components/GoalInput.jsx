import React, { useState } from 'react';

export default function GoalInput({ onSubmit, loading }) {
  const [goal, setGoal] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!goal.trim() || loading) return;
    onSubmit(goal.trim());
    setGoal('');
  };

  return (
    <form className="goal-form" onSubmit={handleSubmit}>
      <input
        className="goal-input"
        type="text"
        placeholder="e.g., Help me stay consistent with DSA prep"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        disabled={loading}
      />
      <button className="generate-btn" type="submit" disabled={!goal.trim() || loading}>
        {loading ? 'Generating...' : 'Generate Workflow'}
      </button>
    </form>
  );
}