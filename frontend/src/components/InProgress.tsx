import React from 'react';
import { Result } from 'antd';

interface InProgressProps {
  feature: string;
}

const InProgress: React.FC<InProgressProps> = ({ feature }) => {
  return (
    <Result
      status="info"
      title={`${feature} is coming soon!`}
      subTitle="This feature is currently under development. Check back later for updates."
    />
  );
};

export default InProgress;
