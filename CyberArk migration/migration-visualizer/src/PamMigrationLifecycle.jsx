import React, { useState } from 'react';

// --- Data for the Migration Lifecycle ---
// This data is derived from the project's README and agent analysis.
const lifecycleSteps = [
    {
        phase: 'P1',
        title: 'Discovery & Mapping',
        summary: 'The journey begins. The agent system scans the on-prem environment to identify and inventory the SQL Server account.',
        agent: 'Agent 01 (Discovery)',
        details: [
            'Agent connects to the on-prem CyberArk PVWA API.',
            'Queries for all accounts, safes, and platforms.',
            'Identifies the target SQL Server account based on its properties.',
            'Maps its dependencies, such as which applications use it.',
            'Outputs a "Discovery Manifest" for the next phases.',
        ],
        status: 'Identified',
    },
    {
        phase: 'P3',
        title: 'Policy & Safe Preparation',
        summary: 'Before the move, the new home is prepared. The target safe and policies are created in Privilege Cloud.',
        agent: 'Agent 03 (Permissions)',
        details: [
            'Agent analyzes the on-prem safe and policy structure.',
            'A plan is created to replicate the permissions and settings in the cloud.',
            'Using the Privilege Cloud API, the agent creates the new safe.',
            'Applies the necessary policy rules and grants permissions for users/groups.',
        ],
        status: 'Safe Prepared',
    },
    {
        phase: 'P4/P5',
        title: 'ETL Migration',
        summary: 'The core migration. The account is securely extracted, transformed, and loaded into the Privilege Cloud.',
        agent: 'Agent 04 (ETL Orchestration)',
        details: [
            '1. **FREEZE**: CPM management is disabled for the on-prem account via API to prevent changes.',
            '2. **EXPORT**: The agent retrieves the account details and its current password securely.',
            '3. **TRANSFORM**: The account data is mapped to the Privilege Cloud format.',
            '4. **IMPORT**: The agent uses the PCloud API to create the account in the target safe with its retrieved password.',
            '5. **UNFREEZE**: CPM management is re-enabled for the on-prem account.',
        ],
        status: 'Migrated to Cloud',
    },
    {
        phase: 'P4/P5',
        title: 'Heartbeat & Validation',
        summary: 'Post-migration check. The agent system verifies that the newly migrated account is alive and well.',
        agent: 'Agent 05 (Heartbeat)',
        details: [
            'Agent connects to the Privilege Cloud API.',
            'Triggers an immediate "Verify" action on the new account.',
            'The Privilege Cloud CPM attempts to log in to the SQL Server using the stored credentials.',
            'The result (success or failure) is recorded.',
            'This confirms the credential is functional in its new environment.',
        ],
        status: 'Validated in Cloud',
    },
    {
        phase: 'P6',
        title: 'Integration Repointing',
        summary: 'Applications that used the old credential are now updated to point to the new one in Privilege Cloud.',
        agent: 'Agent 06 (Integration)',
        details: [
            'The agent scans application code and configuration files.',
            'Identifies hardcoded references to the on-prem CyberArk CCP/AAM.',
            'Automatically replaces old connection details with new Privilege Cloud pointers.',
            'A change registry is maintained for tracking and potential rollback.',
        ],
        status: 'Integrations Updated',
    },
    {
        phase: 'P7',
        title: 'Decommission',
        summary: 'The final step. The original on-prem account is removed, completing its lifecycle.',
        agent: 'Agent 07 (Compliance)',
        details: [
            'After a parallel running period, the on-prem account is scheduled for deletion.',
            'Agent 07 ensures all compliance and audit requirements are met.',
            'The on-prem account is formally decommissioned.',
            'Final reports are generated for audit and sign-off.',
        ],
        status: 'Decommissioned',
    },
];

// --- React Component for a Single Blade Card ---
const BladeCard = ({ step, index }) => {
    const [isOpen, setIsOpen] = useState(false);

    const cardStyle = {
        background: '#fff',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        marginBottom: '20px',
        overflow: 'hidden',
        transition: 'all 0.3s ease-in-out',
        borderLeft: `5px solid #007bff`,
    };

    const headerStyle = {
        padding: '20px',
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    };

    const contentStyle = {
        padding: '0 20px',
        maxHeight: isOpen ? '500px' : '0',
        overflow: 'hidden',
        transition: 'max-height 0.4s ease-in-out, padding 0.4s ease-in-out',
        paddingTop: isOpen ? '10px': '0',
        paddingBottom: isOpen ? '20px' : '0',
    };
    
    const statusPillStyle = {
        background: '#e7f3ff',
        color: '#007bff',
        padding: '5px 12px',
        borderRadius: '16px',
        fontSize: '12px',
        fontWeight: 'bold',
    };

    return (
        <div style={cardStyle}>
            <div style={headerStyle} onClick={() => setIsOpen(!isOpen)}>
                <div>
                    <h3 style={{ margin: 0, color: '#333' }}>{step.phase}: {step.title}</h3>
                    <p style={{ margin: '5px 0 0', color: '#666', fontSize: '14px' }}>{step.summary}</p>
                </div>
                <div style={{ textAlign: 'right', marginLeft: '20px' }}>
                    <div style={statusPillStyle}>{step.status}</div>
                    <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#ccc', marginTop: '10px', display: 'block' }}>{isOpen ? '−' : '+'}</span>
                </div>
            </div>
            <div style={contentStyle}>
                <h4 style={{ color: '#007bff', borderBottom: '1px solid #eee', paddingBottom: '5px' }}>Agent Responsible: {step.agent}</h4>
                <ul style={{ listStyleType: 'disc', paddingLeft: '20px' }}>
                    {step.details.map((detail, i) => (
                        <li key={i} style={{ marginBottom: '8px', fontSize: '14px', lineHeight: '1.6' }}>{detail}</li>
                    ))}
                </ul>
            </div>
        </div>
    );
};


// --- Main Component to Render the Lifecycle Visualization ---
const PamMigrationLifecycle = () => {
    const containerStyle = {
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        background: '#f4f7f9',
        padding: '40px',
        maxWidth: '900px',
        margin: '0 auto',
    };

    const titleStyle = {
        textAlign: 'center',
        color: '#222',
        marginBottom: '10px',
    };
    
    const subtitleStyle = {
        textAlign: 'center',
        color: '#555',
        marginBottom: '40px',
        fontSize: '16px'
    };

    return (
        <div style={containerStyle}>
            <h1 style={titleStyle}>PAM File Migration Lifecycle</h1>
            <p style={subtitleStyle}>Visualizing the automated journey of a SQL Server credential to the Privilege Cloud.</p>
            <div>
                {lifecycleSteps.map((step, index) => (
                    <BladeCard key={index} step={step} index={index} />
                ))}
            </div>
        </div>
    );
};

export default PamMigrationLifecycle;
