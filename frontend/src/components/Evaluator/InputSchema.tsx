import { Row, Typography } from "antd";
import { HighlightOutlined } from '@ant-design/icons';
const { Paragraph } = Typography;

export default function InputSchema({configField, evaluator, setEvaluator}) {
    return (<>
     <Row>
          <Typography.Text>{configField}</Typography.Text>
          </Row>
          <Paragraph
          editable={{
            icon: <HighlightOutlined />,
            tooltip: 'click to edit text',
            onChange: ((e) => setEvaluator({ ...evaluator, config: {...evaluator.config, [configField]:e } })),
            enterIcon: null,
          }}
          >
            {JSON.stringify(evaluator.config[configField])}
          </Paragraph>
    </>)
}