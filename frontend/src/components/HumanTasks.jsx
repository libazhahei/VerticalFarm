import React from 'react';
import { useTheme } from '@mui/material';
import { Assignment as TaskIcon } from '@mui/icons-material';
import SectionCard from './SectionCard';
import TaskItem from './TaskItem';

const HumanTasks = ({
  tasks,
  loading,
  error
}) => {
  const materialTheme = useTheme();

  return (
    <SectionCard
      title="Human Tasks"
      icon={TaskIcon}
      color={materialTheme.palette.warning.main}
      loading={loading}
      error={error}
      isEmpty={tasks.length === 0}
      emptyMessage="No human tasks required"
    >
      {tasks.map((task, idx) => (
        <TaskItem
          key={idx}
          task={task.task}
          todo={task.todo}
        />
      ))}
    </SectionCard>
  );
};

export default HumanTasks;
