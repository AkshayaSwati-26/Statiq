/**
 * Formats API errors (especially FastAPI validation errors) into clean, human-readable strings.
 */
export const getErrorMessage = (err, defaultMsg) => {
  if (!err) return defaultMsg;
  
  // Extract detail from Axios response
  const detail = err.response?.data?.detail;
  
  if (!detail) {
    return err.message || defaultMsg;
  }
  
  if (typeof detail === 'string') {
    return detail;
  }
  
  if (Array.isArray(detail)) {
    return detail
      .map(d => {
        const field = d.loc
          ? d.loc.filter(locItem => locItem !== 'body' && locItem !== 'query').join('.')
          : '';
        return `${field ? field + ': ' : ''}${d.msg}`;
      })
      .join(', ');
  }
  
  if (typeof detail === 'object') {
    return JSON.stringify(detail);
  }
  
  return String(detail);
};
