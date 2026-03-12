# Firestore Database Schema

## Collections Structure

### 1. users/
```
users/{uid}/
├── uid: string
├── email: string
├── name: string
├── created_at: timestamp
├── verified: boolean
├── last_login: timestamp
│
├── eeg_files/ (subcollection)
│  └── {file_id}/
│     ├── file_id: string
│     ├── original_filename: string
│     ├── file_size: number
│     ├── upload_date: timestamp
│     └── processing_status: string
│
└── predictions/ (subcollection)
   └── {prediction_id}/
      ├── prediction_id: string
      ├── file_id: string
      ├── depression_probability: number
      ├── risk_level: string
      ├── confidence: number
      ├── created_at: timestamp
      └── explanation: object (SHAP data)
```

### 2. admins/
```
admins/{uid}/
├── uid: string
├── email: string
├── name: string
├── role: string (admin, super_admin)
├── verified: boolean
├── created_at: timestamp
├── last_login: timestamp
└── permissions: object
   ├── view_users: boolean
   ├── view_analytics: boolean
   ├── manage_system: boolean
   └── manage_admins: boolean
```

### 3. otp_codes/
```
otp_codes/{email}/
├── email: string
├── code: string (6 digits)
├── attempts: number
├── created_at: timestamp
├── expires_at: timestamp
└── verified: boolean
```

### 4. system_settings/ (optional)
```
system_settings/config
├── debug_mode: boolean
├── log_level: string
├── max_file_size: number
└── otp_expiry: number
```

### 5. system_logs/ (optional)
```
system_logs/{log_id}
├── timestamp: timestamp
├── level: string (DEBUG, INFO, WARNING, ERROR)
├── message: string
├── user_id: string (optional)
└── details: object
```

## Indexes

Key indexes for performance:
- `users.created_at` - Sort by creation date
- `predictions.created_at` - Sort predictions
- `otp_codes.expires_at` - Cleanup expired OTPs
- `admins.email` - Find admin by email

## Security Rules
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
      
      // Patients and predictions under user
      match /{document=**} {
        allow read, write: if request.auth.uid == userId;
      }
    }
    
    // Admins collection
    match /admins/{adminId} {
      allow read, write: if request.auth.token.admin == true;
    }
  }
}
```
