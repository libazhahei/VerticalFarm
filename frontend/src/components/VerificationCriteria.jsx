import React from 'react';
import { useTheme } from '@mui/material';
import { VerifiedUser as VerificationIcon } from '@mui/icons-material';
import SectionCard from './SectionCard';
import TaskItem from './TaskItem';

const VerificationCriteria = ({
  verification,
  loading,
  error
}) => {
  const materialTheme = useTheme();

  return (
    <SectionCard
      title="Verification Criteria"
      icon={VerificationIcon}
      color={materialTheme.palette.info.main}
      loading={loading}
      error={error}
      isEmpty={verification.length === 0}
      emptyMessage="No verification items"
    >
      {verification.map((item, idx) => (
        <TaskItem
          key={idx}
          task={item.task}
          todo={item.todo}
          type="verification"
        />
      ))}
    </SectionCard>
  );
};

export default VerificationCriteria;
