import { Col, Flex, Row, Typography } from "antd";
import { HighlightOutlined } from '@ant-design/icons';
const { Paragraph } = Typography;

export default function LLMConfig({ llmConfigField, evaluator, setEvaluator }) {
    return (<>
        <Flex gap="middle">
            <Row>
                <Typography.Text strong={true}>{llmConfigField}: </Typography.Text>
                    <Paragraph
                        editable={{
                            icon: <HighlightOutlined />,
                            tooltip: 'click to edit text',
                            onChange: ((e) => setEvaluator({ ...evaluator, [llmConfigField]: e })),
                            enterIcon: null,
                        }}
                    >
                        {evaluator[llmConfigField]}
                    </Paragraph>
            </Row>
        </Flex>
    </>)
}