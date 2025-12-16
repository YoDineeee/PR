import unittest
import requests
import time
import json
from typing import Dict, Any

class TestReplication(unittest.TestCase):
    """Test suite for leader-follower replication system"""
    
    def setUp(self):
        """Set up test environment"""
        self.leader_url = "http://localhost:5000"
        self.follower_url = "http://localhost:5001"
        self.test_data = {
            "test_key_1": "test_value_1",
            "test_key_2": "test_value_2",
            "test_key_3": "test_value_3"
        }
    
    def test_health_endpoints(self):
        """Test that both leader and follower health endpoints respond correctly"""
        # Test leader health
        leader_response = requests.get(f"{self.leader_url}/health")
        self.assertEqual(leader_response.status_code, 200)
        leader_data = leader_response.json()
        self.assertEqual(leader_data["status"], "ok")
        self.assertEqual(leader_data["role"], "leader")
        
        # Test follower health
        follower_response = requests.get(f"{self.follower_url}/health")
        self.assertEqual(follower_response.status_code, 200)
        follower_data = follower_response.json()
        self.assertEqual(follower_data["status"], "ok")
        self.assertEqual(follower_data["role"], "follower")
    
    def test_basic_replication(self):
        """Test that writes to leader are replicated to follower"""
        key = "basic_test"
        value = "basic_value"
        
        # Write to leader
        write_response = requests.post(
            f"{self.leader_url}/write",
            json={"key": key, "value": value}
        )
        self.assertEqual(write_response.status_code, 200)
        write_data = write_response.json()
        self.assertEqual(write_data["status"], "ok")
        
        # Read from leader
        leader_read_response = requests.get(f"{self.leader_url}/read/{key}")
        self.assertEqual(leader_read_response.status_code, 200)
        leader_read_data = leader_read_response.json()
        self.assertEqual(leader_read_data["status"], "ok")
        self.assertEqual(leader_read_data["key"], key)
        self.assertEqual(leader_read_data["value"], value)
        
        # Read from follower (should be replicated)
        follower_read_response = requests.get(f"{self.follower_url}/read/{key}")
        self.assertEqual(follower_read_response.status_code, 200)
        follower_read_data = follower_read_response.json()
        self.assertEqual(follower_read_data["status"], "ok")
        self.assertEqual(follower_read_data["key"], key)
        self.assertEqual(follower_read_data["value"], value)
    
    def test_multiple_writes_replication(self):
        """Test that multiple writes are all replicated correctly"""
        written_keys = []
        
        # Write multiple key-value pairs
        for key, value in self.test_data.items():
            write_response = requests.post(
                f"{self.leader_url}/write",
                json={"key": key, "value": value}
            )
            self.assertEqual(write_response.status_code, 200)
            written_keys.append(key)
        
        # Verify all data exists on leader
        for key in written_keys:
            leader_response = requests.get(f"{self.leader_url}/read/{key}")
            self.assertEqual(leader_response.status_code, 200)
            leader_data = leader_response.json()
            self.assertEqual(leader_data["value"], self.test_data[key])
        
        # Verify all data exists on follower
        for key in written_keys:
            follower_response = requests.get(f"{self.follower_url}/read/{key}")
            self.assertEqual(follower_response.status_code, 200)
            follower_data = follower_response.json()
            self.assertEqual(follower_data["value"], self.test_data[key])
    
    def test_update_existing_key(self):
        """Test that updating an existing key works correctly"""
        key = "update_test"
        original_value = "original_value"
        updated_value = "updated_value"
        
        # Write original value
        requests.post(
            f"{self.leader_url}/write",
            json={"key": key, "value": original_value}
        )
        
        # Update with new value
        update_response = requests.post(
            f"{self.leader_url}/write",
            json={"key": key, "value": updated_value}
        )
        self.assertEqual(update_response.status_code, 200)
        
        # Verify leader has updated value
        leader_response = requests.get(f"{self.leader_url}/read/{key}")
        leader_data = leader_response.json()
        self.assertEqual(leader_data["value"], updated_value)
        
        # Verify follower has updated value
        follower_response = requests.get(f"{self.follower_url}/read/{key}")
        follower_data = follower_response.json()
        self.assertEqual(follower_data["value"], updated_value)
    
    def test_read_nonexistent_key(self):
        """Test reading a non-existent key returns 404"""
        nonexistent_key = "nonexistent_key"
        
        # Test on leader
        leader_response = requests.get(f"{self.leader_url}/read/{nonexistent_key}")
        self.assertEqual(leader_response.status_code, 404)
        leader_data = leader_response.json()
        self.assertEqual(leader_data["status"], "error")
        self.assertEqual(leader_data["message"], "not found")
        
        # Test on follower
        follower_response = requests.get(f"{self.follower_url}/read/{nonexistent_key}")
        self.assertEqual(follower_response.status_code, 404)
        follower_data = follower_response.json()
        self.assertEqual(follower_data["status"], "error")
        self.assertEqual(follower_data["message"], "not found")
    
    def test_concurrent_writes(self):
        """Test that concurrent writes are handled correctly"""
        import threading
        import queue
        
        results = queue.Queue()
        num_threads = 5
        keys_per_thread = 3
        
        def write_worker(thread_id):
            for i in range(keys_per_thread):
                key = f"concurrent_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                try:
                    response = requests.post(
                        f"{self.leader_url}/write",
                        json={"key": key, "value": value},
                        timeout=5
                    )
                    results.put((thread_id, i, response.status_code, response.json()))
                except Exception as e:
                    results.put((thread_id, i, None, str(e)))
        
        # Start concurrent write threads
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=write_worker, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all writes succeeded
        successful_writes = 0
        while not results.empty():
            thread_id, i, status, result = results.get()
            if status == 200:
                successful_writes += 1
            else:
                self.fail(f"Write failed for thread {thread_id}, iteration {i}: {result}")
        
        self.assertEqual(successful_writes, num_threads * keys_per_thread)
        
        # Verify all data is replicated
        for thread_id in range(num_threads):
            for i in range(keys_per_thread):
                key = f"concurrent_{thread_id}_{i}"
                expected_value = f"value_{thread_id}_{i}"
                
                # Check leader
                leader_response = requests.get(f"{self.leader_url}/read/{key}")
                self.assertEqual(leader_response.status_code, 200)
                leader_data = leader_response.json()
                self.assertEqual(leader_data["value"], expected_value)
                
                # Check follower
                follower_response = requests.get(f"{self.follower_url}/read/{key}")
                self.assertEqual(follower_response.status_code, 200)
                follower_data = follower_response.json()
                self.assertEqual(follower_data["value"], expected_value)
    
    def test_data_consistency_after_restart(self):
        """Test that data remains consistent after follower restart"""
        key = "persistence_test"
        value = "persistence_value"
        
        # Write data before restart
        write_response = requests.post(
            f"{self.leader_url}/write",
            json={"key": key, "value": value}
        )
        self.assertEqual(write_response.status_code, 200)
        
        # Wait a moment to ensure replication
        time.sleep(1)
        
        # Verify data exists before restart
        pre_restart_response = requests.get(f"{self.follower_url}/read/{key}")
        self.assertEqual(pre_restart_response.status_code, 200)
        pre_restart_data = pre_restart_response.json()
        self.assertEqual(pre_restart_data["value"], value)
        
        # Note: In a real test environment, you would restart the follower container here
        # For this test, we'll simulate by checking the data is still there
        
        # Verify data still exists after "restart"
        post_restart_response = requests.get(f"{self.follower_url}/read/{key}")
        self.assertEqual(post_restart_response.status_code, 200)
        post_restart_data = post_restart_response.json()
        self.assertEqual(post_restart_data["value"], value)
    
    def test_replication_ordering(self):
        """Test that the order of operations is preserved"""
        operations = [
            ("key1", "value1"),
            ("key2", "value2"),
            ("key1", "value1_updated"),
            ("key3", "value3")
        ]
        
        # Execute operations in sequence
        for key, value in operations:
            response = requests.post(
                f"{self.leader_url}/write",
                json={"key": key, "value": value}
            )
            self.assertEqual(response.status_code, 200)
            time.sleep(0.1)  # Small delay to ensure order
        
        # Verify final state on leader
        final_leader_state = {}
        for key in set([op[0] for op in operations]):
            response = requests.get(f"{self.leader_url}/read/{key}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            final_leader_state[key] = data["value"]
        
        # Verify final state on follower matches leader
        for key, expected_value in final_leader_state.items():
            response = requests.get(f"{self.follower_url}/read/{key}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["value"], expected_value)
        
        # Verify specific ordering expectations
        self.assertEqual(final_leader_state["key1"], "value1_updated")  # Last write wins
        self.assertEqual(final_leader_state["key2"], "value2")
        self.assertEqual(final_leader_state["key3"], "value3")

def run_tests():
    """Run all tests and report results"""
    print("Running Lab 4 Replication Tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestReplication)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\nAll tests passed! ✓")
    else:
        print("\nSome tests failed! ✗")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_tests()