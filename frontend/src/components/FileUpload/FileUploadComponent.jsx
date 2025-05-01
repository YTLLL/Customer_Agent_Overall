import React, { useState, useRef } from 'react';
import { 
  Paper, 
  Typography, 
  Box 
} from '@mui/material';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import './FileUploadComponent.css';

const FileUploadComponent = ({ onFileChange }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  
  // Handle drag events
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };
  
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) {
      setIsDragging(true);
    }
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
      e.dataTransfer.clearData();
    }
  };
  
  // Handle file input change
  const handleChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };
  
  // Process files
  const handleFiles = (fileList) => {
    const validFiles = Array.from(fileList).filter(file => {
      const fileType = file.type.toLowerCase();
      return (
        fileType === 'application/pdf' ||
        fileType === 'image/png' ||
        fileType === 'image/jpeg' ||
        fileType === 'image/jpg'
      );
    });
    
    if (validFiles.length > 0) {
      setFiles(prevFiles => [...prevFiles, ...validFiles]);
      if (onFileChange) {
        onFileChange(validFiles);
      }
    } else {
      alert('Please upload only PDF, PNG, JPG, or JPEG files.');
    }
  };
  
  // Trigger file input click
  const handleChooseFiles = () => {
    fileInputRef.current.click();
  };
  
  return (
    <Box className="form-field">
      <Typography variant="caption" className="field-label">
        File Upload *
      </Typography>
      <Paper 
        variant="outlined" 
        sx={{ 
          p: 2, 
          height: '180px', 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          backgroundColor: 'transparent',
          border: isDragging 
            ? '2px dashed #00e676' 
            : '1px dashed rgba(255, 255, 255, 0.3)',
          transition: 'all 0.2s ease-in-out'
        }}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleChange}
          accept=".pdf,.png,.jpg,.jpeg"
          style={{ display: 'none' }}
        />
        
        {files.length > 0 ? (
          <Box sx={{ width: '100%' }}>
            <Typography variant="body2" gutterBottom>
              {files.length} file(s) selected:
            </Typography>
            <Box sx={{ maxHeight: '100px', overflowY: 'auto' }}>
              {files.map((file, index) => (
                <Typography key={index} variant="caption" display="block" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  {file.name} ({(file.size / 1024).toFixed(2)} KB)
                </Typography>
              ))}
            </Box>
          </Box>
        ) : (
          <>
            <FileUploadIcon sx={{ color: '#00e676', fontSize: 40, mb: 1 }} />
            <Typography variant="body2" align="center">
              Drag & drop files/images here or{' '}
              <Typography 
                component="span" 
                sx={{ 
                  color: '#00e676', 
                  textDecoration: 'underline',
                  cursor: 'pointer'
                }}
                onClick={handleChooseFiles}
              >
                choose files/images
              </Typography>{' '}
              to upload
            </Typography>
            <Typography variant="caption" sx={{ mt: 1, color: 'rgba(255, 255, 255, 0.5)' }}>
              Only export.pdf, png, jpg, jpeg document formats
            </Typography>
          </>
        )}
      </Paper>
    </Box>
  );
};

export default FileUploadComponent;