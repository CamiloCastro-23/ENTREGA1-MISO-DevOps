import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import status
from app.main import get_token, health_check, ping, reset_database, check_blacklist, add_to_blacklist, BlacklistCreateRequest, BlacklistEntry, get_db
from app.main import DATABASE_URL, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

class TestRootAndDeployEndpoints(unittest.TestCase):

    def test_health_check(self):
        """Test the health_check function directly"""
        response = health_check()
        self.assertEqual(response, {"status": "OK - Pipeline de CI/CD con FastAPI"})

    @patch('socket.gethostname', return_value='mocked-hostname')
    def test_ping(self, mock_gethostname):
        """Test the ping function directly"""
        response = ping()
        self.assertEqual(response['hostname'], 'mocked-hostname')
        self.assertIn(response['deployment_mode'], ['FIRST_DEPLOYMENT', 'BLUE/GREEN'])

    @patch('app.main.Base.metadata.drop_all')  
    @patch('app.main.Base.metadata.create_all')  
    def test_reset_database(self, mock_create_all, mock_drop_all):
        """Test the reset_database function"""
        mock_create_all.return_value = None
        mock_drop_all.return_value = None

        response = reset_database(token=TOKEN)
        self.assertEqual(response['message'], "Base de datos reseteada exitosamente")

    @patch('app.main.Base.metadata.drop_all', side_effect=Exception("Error al eliminar tablas"))
    def test_reset_database_exception(self, mock_drop_all):
        """Test reset_database exception handling"""
        with self.assertRaises(HTTPException) as context:
            reset_database(token=TOKEN)

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Error al resetear la base de datos", context.exception.detail)

    @patch('app.main.SessionLocal', return_value=MagicMock())
    def test_check_blacklist(self, mock_session):
        """Test the check_blacklist function"""
        mock_db = mock_session.return_value
        mock_entry = MagicMock(BlacklistEntry)
        mock_entry.blocked_reason = "Spam"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_entry

        response = check_blacklist(email="test@example.com", token=TOKEN, db=mock_db)
        self.assertTrue(response['is_blacklisted'])
        self.assertEqual(response['blocked_reason'], "Spam")

    @patch('app.main.SessionLocal', return_value=MagicMock())
    def test_check_blacklist_not_found(self, mock_session):
        """Test the check_blacklist function when email is not found"""
        mock_db = mock_session.return_value

        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = check_blacklist(email="test@example.com", token=TOKEN, db=mock_db)
        self.assertFalse(response['is_blacklisted'])
        self.assertIsNone(response['blocked_reason'])

    @patch('app.main.SessionLocal', return_value=MagicMock())
    def test_add_to_blacklist(self, mock_session):
        """Test adding an email to blacklist with mocked database"""
        mock_db = mock_session.return_value
        mock_db.query.return_value.filter.return_value.first.return_value = None 

        request_data = BlacklistCreateRequest(
            email="test@example.com",
            app_uuid="123e4567-e89b-12d3-a456-426614174000",
            blocked_reason="Spam"
        )

        request = MagicMock()
        request.client.host = "127.0.0.1" 

        response = add_to_blacklist(request_data, request, token=TOKEN, db=mock_db)
        self.assertEqual(response['message'], "Email agregado a la lista negra exitosamente")

    @patch('app.main.SessionLocal', return_value=MagicMock())
    def test_add_to_blacklist_already_exists(self, mock_session):
        """Test adding an email that is already in the blacklist"""
        mock_db = mock_session.return_value
        mock_entry = MagicMock(BlacklistEntry)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_entry 

        request_data = BlacklistCreateRequest(
            email="test@example.com",
            app_uuid="123e4567-e89b-12d3-a456-426614174000",
            blocked_reason="Spam"
        )

        request = MagicMock()
        request.client.host = "127.0.0.1"  

        with self.assertRaises(HTTPException) as context:
            add_to_blacklist(request_data, request, token=TOKEN, db=mock_db)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "El email ya está en la lista negra")

    def test_get_token_valid(self):
        credentials = MagicMock(HTTPAuthorizationCredentials)
        credentials.scheme = "Bearer"
        credentials.credentials = TOKEN
        assert get_token(credentials) == TOKEN

    # def test_get_token_invalid_scheme(self):
    #     credentials = MagicMock(HTTPAuthorizationCredentials)
    #     credentials.scheme = "InvalidScheme"
    #     credentials.credentials = TOKEN
        
    #     with self.assertRaises(HTTPException) as context:
    #         get_token(credentials)
    #     assert context.exception.status_code == status.HTTP_401_UNAUTHORIZED

    # def test_get_token_invalid_credentials(self):
    #     credentials = MagicMock(HTTPAuthorizationCredentials)
    #     credentials.scheme = "Bearer"
    #     credentials.credentials = "invalid_token"
        
    #     with self.assertRaises(HTTPException) as context:
    #         get_token(credentials)
    #     assert context.exception.status_code == status.HTTP_401_UNAUTHORIZED

    # def test_get_db(self):
    #     with patch('app.main.SessionLocal', return_value=MagicMock()) as mock_session:
    #         mock_db = mock_session.return_value
    #         generator = get_db()
    #         db = next(generator)
    #         mock_session.assert_called_once()
    #         assert db == mock_db
    #         with patch.object(mock_db, 'close') as mock_close:
    #             try:
    #                 next(generator)
    #             except StopIteration:
    #                 pass
    #             mock_close.assert_called_once()


